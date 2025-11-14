import logging
import uuid

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import redirect
from rest_framework import generics, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Transaction, Wallet, WithdrawalRequest
from .serializers import (
    AdminWithdrawalRequestUpdateSerializer,
    CreateWithdrawalRequestSerializer,
    PaymentSerializer,
    TransactionSerializer,
    WalletSerializer,
    WithdrawalRequestSerializer,
)
from .services import ZibalService
from .tasks import verify_deposit_task

logger = logging.getLogger(__name__)


class DepositAPIView(generics.GenericAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]
        user = request.user

        try:
            wallet = user.wallet
        except Wallet.DoesNotExist:
            return Response(
                {"error": "Wallet not found for this user."},
                status=status.HTTP_404_NOT_FOUND,
            )

        order_id = str(uuid.uuid4())
        transaction = Transaction.objects.create(
            wallet=wallet,
            amount=amount,
            transaction_type="deposit",
            order_id=order_id,
            status="pending",
            description="Wallet deposit",
        )

        zibal = ZibalService()
        callback_url = request.build_absolute_uri("/api/wallet/verify-deposit/")
        mobile_number = (
            f"0{user.phone_number.national_number}" if user.phone_number else None
        )

        zibal_response = zibal.create_payment(
            amount=int(amount),
            description=f"Wallet deposit for order {order_id}",
            callback_url=callback_url,
            order_id=order_id,
            mobile=mobile_number,
        )

        track_id = zibal_response.get("trackId")
        if track_id:
            transaction.authority = str(track_id)
            transaction.save()
            payment_url = zibal.generate_payment_url(track_id)
            return Response({"payment_url": payment_url}, status=status.HTTP_200_OK)

        transaction.status = "failed"
        transaction.description = zibal_response.get(
            "message", "Failed to create payment."
        )
        transaction.save()

        error_message = zibal_response.get("message") or "Failed to create payment."
        logger.error(
            "Zibal deposit creation failed for user %s (order %s): %s",
            user.id,
            order_id,
            error_message,
        )
        return Response(
            {"error": error_message},
            status=status.HTTP_400_BAD_REQUEST,
        )


class VerifyDepositAPIView(APIView):
    def get(self, request, *args, **kwargs):
        track_id = request.query_params.get("trackId")
        success = request.query_params.get("success")
        order_id = request.query_params.get("orderId")

        if not track_id or not order_id:
            logger.warning("Zibal callback missing trackId or orderId.")
            # Redirect to a generic failure page if we don't have enough info
            return redirect(settings.ZIBAL_PAYMENT_FAILED_URL)

        if success != "1":
            # If the payment was not successful according to Zibal, no need to verify.
            # We can optionally update our transaction status to 'cancelled' or 'failed' here.
            try:
                tx = Transaction.objects.get(order_id=order_id, authority=track_id, status="pending")
                tx.status = "failed"
                tx.description = "Payment canceled by user or failed at gateway."
                tx.save()
            except Transaction.DoesNotExist:
                # If transaction not found, we can't do much. Log it.
                logger.error(f"Transaction not found for failed payment callback. order_id={order_id}, track_id={track_id}")
            return redirect(settings.ZIBAL_PAYMENT_FAILED_URL)

        # Instead of verifying here, queue a Celery task.
        verify_deposit_task.delay(track_id=track_id, order_id=order_id)

        # Redirect the user to a pending/processing page.
        # This URL should be defined in your settings.
        processing_url = getattr(settings, 'ZIBAL_PAYMENT_PROCESSING_URL', settings.ZIBAL_PAYMENT_SUCCESS_URL)
        return redirect(processing_url)


class WithdrawalRequestAPIView(generics.CreateAPIView):
    serializer_class = CreateWithdrawalRequestSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]
        card_number = serializer.validated_data["card_number"]
        sheba_number = serializer.validated_data["sheba_number"]
        user = request.user

        try:
            wallet = user.wallet
        except Wallet.DoesNotExist:
            return Response({"error": "Wallet not found for this user."}, status=status.HTTP_404_NOT_FOUND)

        if wallet.withdrawable_balance < amount:
            return Response({"error": "موجودی کافی نیست."}, status=status.HTTP_400_BAD_REQUEST)

        if amount < settings.MINIMUM_WITHDRAWAL_AMOUNT:
            return Response(
                {
                    "error": f"حداقل مقدار برداشت {settings.MINIMUM_WITHDRAWAL_AMOUNT:,.0f} ریال است."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check for recent withdrawal requests
        if WithdrawalRequest.objects.filter(
            user=user, created_at__gte=timezone.now() - timedelta(hours=24)
        ).exists():
            return Response(
                {"error": "شما در ۲۴ ساعت گذشته یک درخواست برداشت ثبت کرده‌اید."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update wallet card and sheba number if not already set
        if not wallet.card_number:
            wallet.card_number = card_number
        if not wallet.sheba_number:
            wallet.sheba_number = sheba_number
        wallet.save()

        withdrawal_request = WithdrawalRequest.objects.create(
            user=user,
            amount=amount,
        )
        # Deduct from withdrawable_balance, but hold it until admin approves
        wallet.withdrawable_balance -= amount
        wallet.save()


        return Response(
            WithdrawalRequestSerializer(withdrawal_request).data,
            status=status.HTTP_201_CREATED,
        )


class AdminWithdrawalRequestViewSet(viewsets.ModelViewSet):
    queryset = WithdrawalRequest.objects.all()
    serializer_class = WithdrawalRequestSerializer
    permission_classes = [IsAuthenticated]  # Should be IsAdminUser in a real app

    def get_serializer_class(self):
        if self.action in ["update", "partial_update"]:
            return AdminWithdrawalRequestUpdateSerializer
        return WithdrawalRequestSerializer

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        status = serializer.validated_data.get("status")

        if status is None:
            return Response(
                {"error": "Status is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        if status not in ["approved", "rejected"]:
            return Response(
                {"error": "Invalid status."}, status=status.HTTP_400_BAD_REQUEST
            )

        if instance.status != "pending":
            return Response(
                {"error": f"Request already {instance.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        wallet = instance.user.wallet

        if status == "approved":
            instance.status = "approved"
            Transaction.objects.create(
                wallet=wallet,
                amount=instance.amount,
                transaction_type="withdrawal",
                status="success",
                description=f"Withdrawal request {instance.id} approved by admin.",
            )
        elif status == "rejected":
            instance.status = "rejected"
            wallet.withdrawable_balance += instance.amount
            wallet.save()

        instance.save()
        return Response(WithdrawalRequestSerializer(instance).data)


class WalletViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A viewset for viewing a user's wallet.
    The queryset is filtered to only return the wallet for the currently authenticated user.
    """

    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Wallet.objects.filter(user=self.request.user).prefetch_related(
            "transactions"
        )


class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A viewset for viewing transactions for the user's wallet.
    """

    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Transaction.objects.filter(wallet__user=self.request.user)
            .order_by("-timestamp")
            .select_related("wallet")
        )
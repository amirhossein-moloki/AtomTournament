import logging
import uuid

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import redirect
from django.db import transaction
from rest_framework import generics, status, viewsets
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.throttles import (
    VeryStrictThrottle,
    StrictThrottle,
    MediumThrottle,
)
from .models import Refund, Transaction, Wallet, WithdrawalRequest
from .serializers import (
    AdminWithdrawalRequestUpdateSerializer,
    CreateWithdrawalRequestSerializer,
    RefundRequestSerializer,
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
    throttle_classes = [VeryStrictThrottle]

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

        # Enqueue the verification task.
        verify_deposit_task.delay(track_id=track_id, order_id=order_id)

        # Redirect to a success page. The actual transaction update will happen in the background.
        # The frontend should handle polling or WebSocket updates to reflect the final status.
        return redirect(
            f"{settings.ZIBAL_PAYMENT_SUCCESS_URL}?orderId={order_id}&trackId={track_id}"
        )


class WithdrawalRequestAPIView(generics.CreateAPIView):
    serializer_class = CreateWithdrawalRequestSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [VeryStrictThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]
        card_number = serializer.validated_data["card_number"]
        sheba_number = serializer.validated_data["sheba_number"]
        user = request.user

        try:
            with transaction.atomic():
                wallet = Wallet.objects.select_for_update().get(user=user)

                if wallet.withdrawable_balance < amount or wallet.total_balance < amount:
                    return Response(
                        {"error": "موجودی کافی نیست."}, status=status.HTTP_400_BAD_REQUEST
                    )

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
                # Deduct from balances, but hold it until admin approves
                wallet.total_balance -= amount
                wallet.withdrawable_balance -= amount
                wallet.save()

        except Wallet.DoesNotExist:
            return Response(
                {"error": "Wallet not found for this user."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            WithdrawalRequestSerializer(withdrawal_request).data,
            status=status.HTTP_201_CREATED,
        )


class AdminWithdrawalRequestViewSet(viewsets.ModelViewSet):
    queryset = WithdrawalRequest.objects.all()
    serializer_class = WithdrawalRequestSerializer
    permission_classes = [IsAdminUser]
    throttle_classes = [StrictThrottle]

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

        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(user=instance.user)

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
                wallet.total_balance += instance.amount
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
    throttle_classes = [MediumThrottle]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Wallet.objects.all().prefetch_related("transactions")
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
    throttle_classes = [MediumThrottle]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Transaction.objects.all().order_by("-timestamp").select_related("wallet")
        return (
            Transaction.objects.filter(wallet__user=self.request.user)
            .order_by("-timestamp")
            .select_related("wallet")
        )

# --- New Views based on Zibal Documentation ---

class RefundAPIView(generics.GenericAPIView):
    """
    API view to request a refund for a successful transaction.
    """
    serializer_class = RefundRequestSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [VeryStrictThrottle]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        track_id = serializer.validated_data["track_id"]
        amount = serializer.validated_data.get("amount")

        try:
            transaction_to_refund = Transaction.objects.get(authority=track_id, status='success', wallet__user=request.user)
        except Transaction.DoesNotExist:
            return Response({"error": "تراکنش موفق با این شناسه یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        if transaction_to_refund.is_refunded:
            return Response({"error": "این تراکنش قبلا استرداد شده است."}, status=status.HTTP_400_BAD_REQUEST)

        zibal = ZibalService()
        refund_response = zibal.request_refund(track_id=track_id, amount=int(amount) if amount else None)

        if refund_response.get("result") == 1:
            try:
                with transaction.atomic():
                    refund_data = refund_response.get("data", {})
                    # The status is pending until confirmed by Zibal webhook or further checks
                    new_refund = Refund.objects.create(
                        transaction=transaction_to_refund,
                        amount=amount or transaction_to_refund.amount,
                        refund_id=refund_data.get("refundId"),
                        status=Refund.Status.PENDING,
                        description=refund_response.get("message")
                    )

                    # Mark the original transaction as refunded to prevent double refunds
                    transaction_to_refund.is_refunded = True
                    transaction_to_refund.save()

                return Response({"message": "درخواست استرداد با موفقیت ثبت شد.", "data": refund_response}, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"Could not process refund for track_id {track_id} due to db error: {e}")
                return Response({"error": "خطای داخلی در پردازش استرداد."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({"error": refund_response.get("message", "خطا در استرداد وجه.")}, status=status.HTTP_400_BAD_REQUEST)


class ZibalWalletListView(APIView):
    """
    Lists all wallets available on Zibal for the merchant.
    """
    permission_classes = [IsAdminUser] # Only admins should see the list of all merchant wallets
    throttle_classes = [MediumThrottle]

    def get(self, request, *args, **kwargs):
        zibal = ZibalService()
        wallets_response = zibal.list_wallets()

        if wallets_response.get("result") == 1:
            return Response(wallets_response.get("data"), status=status.HTTP_200_OK)
        else:
            return Response({"error": wallets_response.get("message", "Failed to fetch wallets.")}, status=status.HTTP_400_BAD_REQUEST)

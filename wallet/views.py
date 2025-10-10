import logging

from django.conf import settings
from django.db import transaction
from django.shortcuts import redirect
from rest_framework import generics, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Transaction, Wallet
from .serializers import PaymentSerializer, TransactionSerializer, WalletSerializer
from .services import ZibalService, process_transaction

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

        zibal = ZibalService()
        callback_url = request.build_absolute_uri("/api/wallet/verify-deposit/")
        mobile_number = (
            f"0{user.phone_number.national_number}" if user.phone_number else None
        )

        zibal_response = zibal.create_payment(
            amount=int(amount),
            description="Wallet deposit",
            callback_url=callback_url,
            mobile=mobile_number,
        )

        track_id = zibal_response.get("trackId")

        if track_id:
            Transaction.objects.create(
                wallet=wallet,
                amount=amount,
                transaction_type="deposit",
                authority=str(track_id),
                status="pending",
                description=f"Zibal deposit with trackId {track_id}",
            )
            payment_url = zibal.generate_payment_url(track_id)
            return Response({"payment_url": payment_url}, status=status.HTTP_200_OK)

        error_message = zibal_response.get("message") or "Failed to create payment."
        logger.error(
            "Zibal deposit creation failed for user %s: %s",
            user.id,
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

        if not track_id:
            return redirect(settings.ZIBAL_PAYMENT_FAILED_URL)

        try:
            tx = Transaction.objects.get(authority=track_id)
        except Transaction.DoesNotExist:
            return redirect(settings.ZIBAL_PAYMENT_FAILED_URL)

        if success == "1":
            zibal = ZibalService()
            verification_response = zibal.verify_payment(track_id=track_id)
            if verification_response.get("result") == 100 and verification_response.get(
                "paidAt"
            ):
                try:
                    with transaction.atomic():
                        wallet = Wallet.objects.select_for_update().get(
                            user=tx.wallet.user
                        )
                        if tx.status == "pending":
                            wallet.total_balance += tx.amount
                            wallet.withdrawable_balance += tx.amount
                            wallet.save()
                            tx.status = "success"
                            tx.save()
                    return redirect(settings.ZIBAL_PAYMENT_SUCCESS_URL)
                except Exception as e:
                    logger.error(
                        f"Error processing successful deposit for transaction {tx.id}: {e}"
                    )

        tx.status = "failed"
        tx.save()
        return redirect(settings.ZIBAL_PAYMENT_FAILED_URL)


class WithdrawalAPIView(generics.GenericAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]
        user = request.user

        transaction, error = process_transaction(
            user=user,
            amount=amount,
            transaction_type="withdrawal",
            description="User withdrawal request.",
        )

        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"message": "Withdrawal successful.", "transaction_id": transaction.id},
            status=status.HTTP_200_OK,
        )


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
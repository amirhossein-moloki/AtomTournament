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
from .services import ZarinpalService, process_transaction

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

        zarinpal = ZarinpalService()
        callback_url = request.build_absolute_uri("/api/wallet/verify-deposit/")
        mobile_number = None
        if user.phone_number:
            mobile_number = f"0{user.phone_number.national_number}"

        zarinpal_response = zarinpal.create_payment(
            amount=int(amount),
            description="Wallet deposit",
            callback_url=callback_url,
            email=user.email,
            mobile=mobile_number,
        )

        response_data = zarinpal_response.get("data") or {}
        authority = response_data.get("authority")

        if authority:
            Transaction.objects.create(
                wallet=wallet,
                amount=amount,
                transaction_type="deposit",
                authority=authority,
                status="pending",
                description=f"Zarinpal deposit with authority {authority}",
            )
            payment_url = zarinpal.generate_payment_url(authority)
            return Response({"payment_url": payment_url}, status=status.HTTP_200_OK)

        error_message = zarinpal_response.get("error") or response_data.get("message")
        logger.error(
            "Zarinpal deposit creation failed for user %s: %s",
            user.id,
            error_message or "unknown error",
        )
        return Response(
            {"error": error_message or "Failed to create payment."},
            status=status.HTTP_400_BAD_REQUEST,
        )


class VerifyDepositAPIView(APIView):
    def get(self, request, *args, **kwargs):
        authority = request.query_params.get("Authority")
        zarinpal_status = request.query_params.get("Status")

        try:
            tx = Transaction.objects.get(authority=authority)
        except Transaction.DoesNotExist:
            return redirect(settings.ZARINPAL_PAYMENT_FAILED_URL)

        if zarinpal_status == "OK":
            zarinpal = ZarinpalService()
            verification_response = zarinpal.verify_payment(
                amount=int(tx.amount), authority=authority
            )
            verification_data = verification_response.get("data") or {}
            if verification_data.get("code") == 100:
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
                    return redirect(settings.ZARINPAL_PAYMENT_SUCCESS_URL)
                except Exception as e:
                    logger.error(
                        f"Error processing successful deposit for transaction {tx.id}: {e}"
                    )

        tx.status = "failed"
        tx.save()
        return redirect(settings.ZARINPAL_PAYMENT_FAILED_URL)


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
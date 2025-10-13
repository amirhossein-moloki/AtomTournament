import logging
import uuid

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
            return redirect(settings.ZIBAL_PAYMENT_FAILED_URL)

        try:
            tx = Transaction.objects.get(order_id=order_id, authority=track_id)
        except Transaction.DoesNotExist:
            logger.error(
                f"Transaction not found for order_id={order_id} and track_id={track_id}"
            )
            return redirect(settings.ZIBAL_PAYMENT_FAILED_URL)

        if tx.status != "pending":
            logger.warning(
                f"Verification attempt on already processed transaction {tx.id} with status {tx.status}"
            )
            # Redirect based on final status to avoid reprocessing
            if tx.status == "success":
                return redirect(settings.ZIBAL_PAYMENT_SUCCESS_URL)
            else:
                return redirect(settings.ZIBAL_PAYMENT_FAILED_URL)

        if success != "1":
            tx.status = "failed"
            tx.description = "Payment canceled by user or failed at gateway."
            tx.save()
            return redirect(settings.ZIBAL_PAYMENT_FAILED_URL)

        zibal = ZibalService()
        verification_response = zibal.verify_payment(track_id=track_id)
        result = verification_response.get("result")

        if result == 100:  # Success
            try:
                with transaction.atomic():
                    # Re-fetch wallet with lock to prevent race conditions
                    wallet = Wallet.objects.select_for_update().get(id=tx.wallet.id)
                    tx.status = "success"
                    tx.ref_number = verification_response.get("refNumber")
                    tx.description = verification_response.get(
                        "description", "Payment successful"
                    )
                    # You might want to save cardNumber securely if needed, here it's just logged
                    card_number = verification_response.get("cardNumber")
                    logger.info(
                        f"Successful payment for tx {tx.id} with card {card_number}"
                    )

                    wallet.total_balance += tx.amount
                    wallet.withdrawable_balance += tx.amount
                    wallet.save()
                    tx.save()
                return redirect(settings.ZIBAL_PAYMENT_SUCCESS_URL)
            except Exception as e:
                logger.error(
                    f"Error processing successful deposit for transaction {tx.id}: {e}"
                )
                # The transaction remains pending for manual/automatic reconciliation
                return redirect(settings.ZIBAL_PAYMENT_FAILED_URL)

        elif result == 201:  # Already verified
            logger.warning(
                f"Zibal reported transaction {tx.id} (trackId: {track_id}) as already verified."
            )
            # Potentially a race condition, let's double check our DB
            if tx.status == "pending":
                # Our DB is out of sync, let's use inquiry to get the final state
                inquiry_response = zibal.inquiry_payment(track_id=track_id)
                if inquiry_response.get("status") == 1: # Paid and verified
                     # Process as success
                    with transaction.atomic():
                        wallet = Wallet.objects.select_for_update().get(id=tx.wallet.id)
                        wallet.total_balance += tx.amount
                        wallet.withdrawable_balance += tx.amount
                        wallet.save()
                        tx.status = "success"
                        tx.ref_number = inquiry_response.get("refNumber")
                        tx.save()
                    return redirect(settings.ZIBAL_PAYMENT_SUCCESS_URL)

            return redirect(settings.ZIBAL_PAYMENT_SUCCESS_URL)

        else:  # Verification failed
            tx.status = "failed"
            tx.description = verification_response.get(
                "message", "Payment verification failed."
            )
            tx.save()
            logger.error(
                f"Zibal verification failed for tx {tx.id} (trackId: {track_id}): {tx.description}"
            )
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
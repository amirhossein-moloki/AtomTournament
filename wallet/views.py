import logging

from django.conf import settings
from django.shortcuts import redirect
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status, viewsets
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError

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
    WalletBalanceSerializer,
    WalletSerializer,
    WithdrawalRequestSerializer,
    ZibalWalletSerializer,
    VerifyDepositSerializer,
)
from .services import WalletService, ZibalService

logger = logging.getLogger(__name__)


class DepositAPIView(generics.GenericAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [VeryStrictThrottle]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]

        service = WalletService(request.user)
        payment_url = service.create_deposit(
            amount=amount,
            callback_url_builder=request.build_absolute_uri
        )
        return Response({"payment_url": payment_url}, status=status.HTTP_200_OK)


@extend_schema(parameters=[VerifyDepositSerializer])
class VerifyDepositAPIView(APIView):
    def get(self, request, *args, **kwargs):
        serializer = VerifyDepositSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        track_id = validated_data["trackId"]
        order_id = validated_data["orderId"]
        success = validated_data["success"]

        redirect_url = settings.ZIBAL_PAYMENT_FAILED_URL
        if success == "1":
            WalletService.verify_and_process_deposit(track_id=track_id, order_id=order_id)
            try:
                tx = Transaction.objects.get(
                    order_id=order_id,
                    authority=track_id,
                )
                if tx.status == Transaction.Status.SUCCESS:
                    redirect_url = f"{settings.ZIBAL_PAYMENT_SUCCESS_URL}?orderId={order_id}&trackId={track_id}"
                else:
                    logger.error(
                        "Payment verification failed after callback.",
                        extra={"order_id": order_id, "track_id": track_id, "status": tx.status},
                    )
            except Transaction.DoesNotExist:
                logger.error(
                    "Transaction not found during payment verification callback.",
                    extra={"order_id": order_id, "track_id": track_id},
                )
        else:
            try:
                tx = Transaction.objects.get(order_id=order_id, authority=track_id, status=Transaction.Status.PENDING)
                tx.status = Transaction.Status.FAILED
                tx.description = "تراکنش ناموفق بود"
                tx.save()
            except Transaction.DoesNotExist:
                logger.error(f"تراکنش در بازگشت ناموفق یافت نشد. order_id={order_id}")

        return redirect(redirect_url)


class WithdrawalRequestAPIView(generics.CreateAPIView):
    serializer_class = CreateWithdrawalRequestSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [VeryStrictThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = WalletService(request.user)
        withdrawal_request = service.create_withdrawal_request(**serializer.validated_data)

        return Response(
            WithdrawalRequestSerializer(withdrawal_request).data,
            status=status.HTTP_201_CREATED,
        )


class AdminWithdrawalRequestViewSet(viewsets.ModelViewSet):
    queryset = (
        WithdrawalRequest.objects.all()
        .select_related('user')
        .select_related('user__wallet')
    )
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
        new_status = serializer.validated_data.get("status")

        if new_status == WithdrawalRequest.Status.APPROVED:
            updated_instance = WalletService.approve_withdrawal_request(instance)
        elif new_status == WithdrawalRequest.Status.REJECTED:
            updated_instance = WalletService.reject_withdrawal_request(instance)
        else:
            raise ValidationError("وضعیت ارسال شده نامعتبر است.")

        return Response(self.get_serializer(updated_instance).data)


class WalletViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [MediumThrottle]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(user=self.request.user).prefetch_related("transactions")

    def get_object(self):
        wallet = super().get_object()
        if wallet.user != self.request.user:
            raise NotFound()
        return wallet


class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [MediumThrottle]

    def get_queryset(self):
        qs = super().get_queryset().select_related("wallet__user")
        return qs.filter(wallet__user=self.request.user).order_by("-timestamp")

    def get_object(self):
        transaction = super().get_object()
        if transaction.wallet.user != self.request.user:
            raise NotFound()
        return transaction


from .serializers import RefundSerializer

class RefundAPIView(generics.GenericAPIView):
    serializer_class = RefundRequestSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [VeryStrictThrottle]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = WalletService(request.user)
        refund = service.create_refund_request(
            track_id=serializer.validated_data["track_id"],
            amount=serializer.validated_data.get("amount")
        )

        response_serializer = RefundSerializer(refund)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(responses=ZibalWalletSerializer(many=True))
class ZibalWalletListView(APIView):
    permission_classes = [IsAdminUser]
    throttle_classes = [MediumThrottle]

    def get(self, request, *args, **kwargs):
        zibal = ZibalService()
        wallets_response = zibal.list_wallets() # This is a direct call for a simple admin tool

        if wallets_response.get("result") == 1:
            return Response(wallets_response.get("data"), status=status.HTTP_200_OK)
        else:
            return Response({"error": wallets_response.get("message", "Failed to fetch wallets.")}, status=status.HTTP_400_BAD_REQUEST)


class WalletBalanceAPIView(generics.RetrieveAPIView):
    serializer_class = WalletBalanceSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        try:
            return self.request.user.wallet
        except Wallet.DoesNotExist:
            raise NotFound("کیف پول برای این کاربر یافت نشد.")

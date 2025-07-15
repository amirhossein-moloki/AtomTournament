from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Transaction, Wallet
from .serializers import TransactionSerializer, WalletSerializer


class WalletViewSet(
    mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    """
    ViewSet for viewing wallets.
    """

    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    @action(detail=True, methods=["post"])
    def deposit(self, request, pk=None):
        """
        Deposit money into the wallet.
        """
        wallet = self.get_object()
        amount = request.data.get("amount")

        if not amount or float(amount) <= 0:
            return Response(
                {"error": "Invalid amount."}, status=status.HTTP_400_BAD_REQUEST
            )

        # In a real-world scenario, you would integrate with a payment gateway here.
        # For now, we'll just simulate a successful deposit.

        wallet.total_balance += float(amount)
        wallet.withdrawable_balance += float(amount)
        wallet.save()

        Transaction.objects.create(
            wallet=wallet, amount=amount, transaction_type="deposit"
        )

        return Response(WalletSerializer(wallet).data)

    @action(detail=True, methods=["post"])
    def withdraw(self, request, pk=None):
        """
        Withdraw money from the wallet.
        """
        wallet = self.get_object()
        amount = request.data.get("amount")

        if not amount or float(amount) <= 0:
            return Response(
                {"error": "Invalid amount."}, status=status.HTTP_400_BAD_REQUEST
            )

        if float(amount) > wallet.withdrawable_balance:
            return Response(
                {"error": "Insufficient balance."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # In a real-world scenario, you would integrate with a payment gateway here.
        # For now, we'll just simulate a successful withdrawal.

        wallet.total_balance -= float(amount)
        wallet.withdrawable_balance -= float(amount)
        wallet.save()

        Transaction.objects.create(
            wallet=wallet, amount=amount, transaction_type="withdrawal"
        )

        return Response(WalletSerializer(wallet).data)


class TransactionViewSet(
    mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    """
    ViewSet for viewing transactions.
    """

    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(wallet__user=self.request.user)


class PaymentViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        amount = request.data.get("amount")
        if not amount or float(amount) <= 0:
            return Response(
                {"error": "Invalid amount."}, status=status.HTTP_400_BAD_REQUEST
            )

        zarinpal_service = ZarinpalService()
        callback_url = request.build_absolute_uri(reverse("payment-verify"))
        response = zarinpal_service.create_payment(
            amount=int(amount),
            description="Wallet charge",
            callback_url=callback_url,
            mobile=request.user.phone_number,
            email=request.user.email,
        )

        if "error" in response:
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        authority = response["data"]["authority"]
        request.session[f"payment_{authority}"] = int(amount)
        payment_url = zarinpal_service.generate_payment_url(authority)
        return Response({"payment_url": payment_url})

    @action(detail=False, methods=["get"])
    def verify(self, request):
        authority = request.query_params.get("Authority")
        status_param = request.query_params.get("Status")

        if not authority or not status_param:
            return Response(
                {"error": "Invalid callback parameters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if status_param != "OK":
            return Response(
                {"error": "Payment failed or canceled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # You should retrieve the amount from your database based on the authority
        # For now, we'll assume the amount is stored in the session
        amount = request.session.get(f"payment_{authority}")
        if not amount:
            return Response(
                {"error": "Invalid authority."}, status=status.HTTP_400_BAD_REQUEST
            )

        zarinpal_service = ZarinpalService()
        response = zarinpal_service.verify_payment(amount, authority)

        if "error" in response:
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        if response["data"]["code"] == 100:
            wallet = request.user.wallet
            wallet.total_balance += float(amount)
            wallet.withdrawable_balance += float(amount)
            wallet.save()
            Transaction.objects.create(
                wallet=wallet, amount=amount, transaction_type="deposit"
            )
            return Response({"message": "Payment verified successfully."})
        elif response["data"]["code"] == 101:
            return Response({"message": "Payment already verified."})
        else:
            return Response(
                {"error": "Payment verification failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Transaction, Wallet
from .serializers import TransactionSerializer, WalletSerializer


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

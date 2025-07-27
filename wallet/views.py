from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from .models import Wallet
from .serializers import WalletSerializer


class WalletViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        "transactions__transaction_type": ["exact"],
        "transactions__timestamp": ["gte", "lte"],
    }

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

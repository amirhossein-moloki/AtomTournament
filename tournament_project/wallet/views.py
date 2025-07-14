from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Wallet, Transaction
from .serializers import WalletSerializer, TransactionSerializer

class WalletViewSet(viewsets.ModelViewSet):
    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

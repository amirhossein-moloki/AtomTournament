from rest_framework import serializers
from .models import Wallet, Transaction

class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ('id', 'user', 'total_balance', 'withdrawable_balance')

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ('id', 'wallet', 'amount', 'transaction_type', 'timestamp')

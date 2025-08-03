from rest_framework import serializers

from .models import Transaction, Wallet


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = "__all__"


class WalletSerializer(serializers.ModelSerializer):
    transactions = TransactionSerializer(many=True, read_only=True)

    class Meta:
        model = Wallet
        fields = "__all__"

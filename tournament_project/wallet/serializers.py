from rest_framework import serializers

from .models import Transaction, Wallet


class WalletSerializer(serializers.ModelSerializer):
    """Serializer for the Wallet model."""

    class Meta:
        model = Wallet
        fields = ("id", "user", "total_balance", "withdrawable_balance")
        read_only_fields = ("id", "user", "total_balance", "withdrawable_balance")


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for the Transaction model."""

    class Meta:
        model = Transaction
        fields = ("id", "wallet", "amount", "transaction_type", "timestamp")
        read_only_fields = ("id", "wallet", "timestamp")

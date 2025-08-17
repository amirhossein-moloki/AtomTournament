from rest_framework import serializers

from .models import Transaction, Wallet


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = (
            "id",
            "wallet",
            "amount",
            "transaction_type",
            "timestamp",
            "description",
        )
        read_only_fields = fields


class WalletSerializer(serializers.ModelSerializer):
    transactions = TransactionSerializer(many=True, read_only=True)

    class Meta:
        model = Wallet
        fields = ("id", "user", "total_balance", "withdrawable_balance", "transactions")
        read_only_fields = fields

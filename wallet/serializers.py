import logging
import re

from rest_framework import serializers

from .models import Transaction, Wallet


logger = logging.getLogger(__name__)


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
        fields = ("id", "user", "total_balance", "withdrawable_balance", "token_balance", "transactions")
        read_only_fields = fields


class PaymentSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=20, decimal_places=2)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive.")

        raw_amount = self.initial_data.get("amount", value)
        digit_count = len(re.findall(r"\d", str(raw_amount)))
        if digit_count > 10:
            logger.warning(
                "Payment amount validation failed: digit limit exceeded",
                extra={"digit_count": digit_count},
            )
            raise serializers.ValidationError(
                "Ensure that there are no more than 10 digits in total."
            )
        return value

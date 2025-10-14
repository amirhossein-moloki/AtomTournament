import logging
import re

from rest_framework import serializers

from .models import Transaction, Wallet, WithdrawalRequest


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
    transactions = TransactionSerializer(many=True, read_only=True, source="latest_transactions")
    summary = serializers.SerializerMethodField()

    class Meta:
        model = Wallet
        fields = (
            "id",
            "user",
            "total_balance",
            "withdrawable_balance",
            "token_balance",
            "transactions",
            "summary",
        )
        read_only_fields = fields

    def get_summary(self, obj):
        from django.db.models import Sum, Count
        summary_data = obj.transactions.aggregate(
            transaction_count=Count('id'),
            total_amount=Sum('amount')
        )
        return {
            "transaction_count": summary_data["transaction_count"] or 0,
            "total_amount": summary_data["total_amount"] or 0,
        }

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        include = self.context.get("request").query_params.get("include")

        if include == "summary":
            # Remove detailed transactions and keep only the summary
            representation.pop("transactions", None)
        else:
            # Remove the summary if we are showing detailed transactions
            representation.pop("summary", None)

        return representation


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


class WithdrawalRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithdrawalRequest
        fields = ('id', 'user', 'amount', 'status', 'created_at', 'updated_at')
        read_only_fields = ('user', 'status', 'created_at', 'updated_at')


class CreateWithdrawalRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    card_number = serializers.CharField(max_length=16)
    sheba_number = serializers.CharField(max_length=26)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive.")
        return value

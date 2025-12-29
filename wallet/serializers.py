import logging
import re

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Refund, Transaction, Wallet, WithdrawalRequest
from common.validators import validate_card_number, validate_sheba


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

    @extend_schema_field(serializers.DictField(child=serializers.CharField()))
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
        request = self.context.get("request")
        if not request:
            return representation

        include = request.query_params.get("include")

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
        return value


class WithdrawalRequestSerializer(serializers.ModelSerializer):
    card_number = serializers.SerializerMethodField()
    sheba_number = serializers.SerializerMethodField()

    def get_card_number(self, obj: WithdrawalRequest):
        if hasattr(obj.user, "wallet"):
            return obj.user.wallet.card_number
        return None

    def get_sheba_number(self, obj: WithdrawalRequest):
        if hasattr(obj.user, "wallet"):
            return obj.user.wallet.sheba_number
        return None

    class Meta:
        model = WithdrawalRequest
        fields = (
            'id',
            'user',
            'amount',
            'card_number',
            'sheba_number',
            'status',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'user',
            'amount',
            'card_number',
            'sheba_number',
            'status',
            'created_at',
            'updated_at',
        )


class AdminWithdrawalRequestUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithdrawalRequest
        fields = ('status',)


class CreateWithdrawalRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=20, decimal_places=2)
    card_number = serializers.CharField(max_length=16, validators=[validate_card_number])
    sheba_number = serializers.CharField(max_length=26, validators=[validate_sheba])

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive.")
        return value


# --- New Serializers for Refund Functionality ---

class RefundRequestSerializer(serializers.Serializer):
    """
    Serializer for validating refund requests.
    """
    track_id = serializers.CharField(max_length=255)
    amount = serializers.DecimalField(max_digits=20, decimal_places=2, required=False)

    def validate_track_id(self, value):
        # Basic validation for track_id format (can be improved)
        if not value.isdigit():
            raise serializers.ValidationError("Track ID must be a numeric value.")
        return value

class RefundSerializer(serializers.ModelSerializer):
    """
    Serializer for the Refund model.
    """
    class Meta:
        model = Refund
        fields = ('id', 'transaction', 'amount', 'refund_id', 'status', 'description', 'created_at')
        read_only_fields = fields


class ZibalWalletSerializer(serializers.Serializer):
    name = serializers.CharField()
    id = serializers.CharField()
    bankName = serializers.CharField()
    accountNumber = serializers.CharField()
    iban = serializers.CharField()


class VerifyDepositSerializer(serializers.Serializer):
    trackId = serializers.CharField()
    success = serializers.CharField()
    orderId = serializers.CharField()

import json
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from zarinpal import ZarinPal
from zarinpal.models import RequestInput, VerifyInput

from .models import Transaction, Wallet


class ZarinpalService:
    def __init__(self):
        self.zarinpal = ZarinPal(
            merchant_id=settings.ZARINPAL_MERCHANT_ID
        )

    def create_payment(
        self, amount, description, callback_url, mobile=None, email=None, currency="IRT"
    ):
        try:
            request_data = RequestInput(
                amount=amount,
                callback_url=callback_url,
                description=description,
                mobile=mobile,
                email=email,
                currency=currency,
            )
            response = self.zarinpal.request(request_data)
            return response.model_dump()
        except Exception as e:
            return {"error": str(e)}

    def verify_payment(self, amount, authority):
        try:
            verify_data = VerifyInput(amount=amount, authority=authority)
            response = self.zarinpal.verify(verify_data)
            return response.model_dump()
        except Exception as e:
            return {"error": str(e)}

    def generate_payment_url(self, authority):
        return self.zarinpal.get_payment_link(authority)


def process_transaction(
    user, amount: Decimal, transaction_type: str, description: str = ""
) -> (Transaction, str):
    """
    Safely processes a transaction by creating a Transaction object and updating
    the user's wallet balance within a single atomic database transaction.
    """
    if amount <= 0:
        return None, "Transaction amount must be positive."

    if transaction_type not in [t[0] for t in Transaction.TRANSACTION_TYPE_CHOICES]:
        return None, f"Invalid transaction type: {transaction_type}"

    try:
        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(user=user)

            is_debit = transaction_type in ["withdrawal", "entry_fee"]

            if is_debit:
                if wallet.withdrawable_balance < amount:
                    return None, "Insufficient withdrawable balance."
                if wallet.total_balance < amount:
                    return None, "Insufficient total balance."

                wallet.total_balance -= amount
                wallet.withdrawable_balance -= amount
            else:  # Credit
                wallet.total_balance += amount
                if transaction_type in ["deposit", "prize"]:
                    wallet.withdrawable_balance += amount

            new_transaction = Transaction.objects.create(
                wallet=wallet,
                amount=amount,
                transaction_type=transaction_type,
                description=description,
                status="success",
            )
            wallet.save()
            return new_transaction, None

    except Wallet.DoesNotExist:
        return None, "User wallet not found."
    except Exception as e:
        return None, str(e)


def process_token_transaction(
    user, amount: Decimal, transaction_type: str, description: str = ""
) -> (Transaction, str):
    """
    Safely processes a token-based transaction by creating a Transaction object
    and updating the user's wallet's token balance within a single atomic
    database transaction.
    """
    if amount <= 0:
        return None, "Transaction amount must be positive."

    if transaction_type not in ["token_spent", "token_earned"]:
        return None, f"Invalid transaction type for tokens: {transaction_type}"

    try:
        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(user=user)

            if transaction_type == "token_spent":
                if wallet.token_balance < amount:
                    return None, "Insufficient token balance."
                wallet.token_balance -= amount
            else:  # token_earned
                wallet.token_balance += amount

            new_transaction = Transaction.objects.create(
                wallet=wallet,
                amount=amount,
                transaction_type=transaction_type,
                description=description,
                status="success",
            )
            wallet.save()
            return new_transaction, None

    except Wallet.DoesNotExist:
        return None, "User wallet not found."
    except Exception as e:
        return None, str(e)

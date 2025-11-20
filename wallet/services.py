import requests
from decimal import Decimal
from datetime import timedelta
import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Transaction, Wallet

logger = logging.getLogger(__name__)


class ZibalService:
    def __init__(self):
        self.merchant_id = getattr(settings, "ZIBAL_MERCHANT_ID", "zibal")
        self.api_base_url = "https://gateway.zibal.ir/v1"

    def create_payment(self, amount, description, callback_url, order_id, mobile=None):
        url = f"{self.api_base_url}/request"
        payload = {
            "merchant": self.merchant_id,
            "amount": amount,
            "callbackUrl": callback_url,
            "description": description,
            "orderId": order_id,
            "mobile": mobile,
        }
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    def verify_payment(self, track_id, amount):
        url = f"{self.api_base_url}/verify"
        payload = {
            "merchant": self.merchant_id,
            "trackId": track_id,
            "amount": amount,
        }
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    def inquiry_payment(self, track_id):
        url = f"{self.api_base_url}/inquiry"
        payload = {"merchant": self.merchant_id, "trackId": track_id}
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    def generate_payment_url(self, track_id):
        return f"https://gateway.zibal.ir/start/{track_id}"


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
                if transaction_type == "withdrawal":
                    # Check for minimum withdrawal amount
                    if amount < settings.MINIMUM_WITHDRAWAL_AMOUNT:
                        return (
                            None,
                            f"Minimum withdrawal amount is {settings.MINIMUM_WITHDRAWAL_AMOUNT} IRR.",
                        )

                    # Check for withdrawal frequency
                    last_withdrawal = (
                        Transaction.objects.filter(
                            wallet=wallet,
                            transaction_type="withdrawal",
                            status="success",
                            timestamp__gte=timezone.now() - timedelta(hours=24),
                        )
                        .order_by("-timestamp")
                        .first()
                    )
                    if last_withdrawal:
                        return (
                            None,
                            "You can only make one withdrawal every 24 hours.",
                        )

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


def verify_and_process_deposit(track_id, order_id):
    """
    Verifies a deposit with Zibal and updates the wallet synchronously.
    This function is designed to be idempotent.
    """
    try:
        tx = Transaction.objects.get(order_id=order_id, authority=track_id)
        if tx.status != "pending":
            logger.warning(
                f"Verification skipped for already processed transaction {tx.id} with status {tx.status}"
            )
            return
    except Transaction.DoesNotExist:
        logger.error(
            f"Transaction not found for order_id={order_id} and track_id={track_id}."
        )
        return

    zibal = ZibalService()
    verification_response = zibal.verify_payment(
        track_id=track_id, amount=int(tx.amount)
    )
    result = verification_response.get("result")

    if result in [100, 201]:
        try:
            with transaction.atomic():
                tx_inside_atomic = Transaction.objects.select_for_update().get(id=tx.id)
                if tx_inside_atomic.status != "pending":
                    logger.warning(
                        f"Transaction {tx.id} was already processed. Skipping update."
                    )
                    return

                wallet = Wallet.objects.select_for_update().get(
                    id=tx_inside_atomic.wallet.id
                )

                wallet.total_balance += tx_inside_atomic.amount
                wallet.withdrawable_balance += tx_inside_atomic.amount
                wallet.save()

                tx_inside_atomic.status = "success"
                tx_inside_atomic.ref_number = verification_response.get("refNumber")
                tx_inside_atomic.description = verification_response.get(
                    "description", "Payment successful"
                )
                tx_inside_atomic.save()
            logger.info(
                f"Successfully verified and processed deposit for transaction {tx.id}"
            )
        except Exception as e:
            logger.error(
                f"Error processing successful deposit for transaction {tx.id}: {e}"
            )
    else:
        tx.status = "failed"
        tx.description = verification_response.get(
            "message", "Payment verification failed."
        )
        tx.save()
        logger.error(
            f"Zibal verification failed for tx {tx.id} (trackId: {track_id}): {tx.description}"
        )


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

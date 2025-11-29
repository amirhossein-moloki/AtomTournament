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
    """
    سرویس برای تعامل با APIهای مختلف زیبال.
    این سرویس شامل متدهایی برای پرداخت، کیف پول، استرداد و گزارش‌گیری است.
    """

    def __init__(self):
        # توکن دسترسی برای APIهای جدید (کیف پول، استرداد و...)
        self.access_token = getattr(settings, "ZIBAL_ACCESS_TOKEN", None)
        # شناسه مرچنت برای APIهای قدیمی درگاه پرداخت
        self.merchant_id = getattr(settings, "ZIBAL_MERCHANT_ID", "zibal")

        self.api_base_url = "https://api.zibal.ir/v1"
        self.gateway_base_url = "https://gateway.zibal.ir/v1"

    def _get_auth_headers(self):
        """هدر احراز هویت را برمی‌گرداند."""
        if not self.access_token:
            raise ValueError("ZIBAL_ACCESS_TOKEN is not configured in settings.")
        return {"Authorization": f"Bearer {self.access_token}"}

    def _post_request(self, url, payload=None, is_gateway=False):
        """یک درخواست POST به سرور زیبال ارسال می‌کند."""
        base_url = self.gateway_base_url if is_gateway else self.api_base_url
        full_url = f"{base_url}{url}"
        headers = {} if is_gateway else self._get_auth_headers()

        try:
            response = requests.post(full_url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error for {full_url}: {e.response.text}")
            return {"error": "HTTP Error", "details": e.response.text}
        except requests.exceptions.RequestException as e:
            logger.error(f"Request Exception for {full_url}: {e}")
            return {"error": str(e)}

    def _get_request(self, url):
        """یک درخواست GET به سرور زیبال ارسال می‌کند."""
        full_url = f"{self.api_base_url}{url}"
        try:
            response = requests.get(full_url, headers=self._get_auth_headers())
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error for {full_url}: {e.response.text}")
            return {"error": "HTTP Error", "details": e.response.text}
        except requests.exceptions.RequestException as e:
            logger.error(f"Request Exception for {full_url}: {e}")
            return {"error": str(e)}

    # --- متدهای درگاه پرداخت ---
    def create_payment(self, amount, description, callback_url, order_id, mobile=None):
        """ایجاد یک تراکنش جدید در درگاه پرداخت."""
        payload = {
            "merchant": self.merchant_id,
            "amount": amount,
            "callbackUrl": callback_url,
            "description": description,
            "orderId": order_id,
            "mobile": mobile,
        }
        return self._post_request("/request", payload, is_gateway=True)

    def verify_payment(self, track_id, amount):
        """تایید یک تراکنش پرداخت."""
        payload = {
            "merchant": self.merchant_id,
            "trackId": track_id,
            "amount": amount,
        }
        return self._post_request("/verify", payload, is_gateway=True)

    def generate_payment_url(self, track_id):
        """URL صفحه پرداخت را تولید می‌کند."""
        return f"https://gateway.zibal.ir/start/{track_id}"

    # --- متدهای کیف پول ---
    def list_wallets(self):
        """لیست کیف پول‌های موجود را برمی‌گرداند."""
        return self._get_request("/wallet/list")

    def get_wallet_balance(self, wallet_id):
        """موجودی یک کیف پول مشخص را برمی‌گرداند."""
        return self._post_request("/wallet/balance", {"id": wallet_id})

    # --- متدهای استرداد وجه ---
    def request_refund(self, track_id, amount=None, card_number=None, description=None):
        """درخواست استرداد وجه برای یک تراکنش موفق."""
        payload = {
            "trackId": track_id,
            "amount": amount,
            "cardNumber": card_number,
            "description": description,
        }
        # حذف کلیدهایی که مقدار ندارند
        payload = {k: v for k, v in payload.items() if v is not None}
        return self._post_request("/account/refund", payload)

    # --- متدهای گزارش‌گیری ---
    def get_checkout_report(self, from_date=None, to_date=None, page=1, size=100):
        """گزارش تسویه‌ها را دریافت می‌کند."""
        payload = {
            "fromDate": from_date,
            "toDate": to_date,
            "page": page,
            "size": size,
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        return self._post_request("/report/checkout", payload)

    def get_gateway_transactions_report(self, from_date=None, to_date=None, page=1, size=100):
        """گزارش تراکنش‌های درگاه پرداخت را دریافت می‌کند."""
        payload = {
            "fromDate": from_date,
            "toDate": to_date,
            "page": page,
            "size": size,
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        return self._post_request("/gateway/report/transaction", payload)


# سایر توابع سرویس لایه که منطق بیزینس را مدیریت می‌کنند
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

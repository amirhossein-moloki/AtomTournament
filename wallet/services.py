import logging
import os
import uuid
from datetime import timedelta
from decimal import Decimal

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError, NotFound

from common.services import HttpClient
from .models import Transaction, Wallet, WithdrawalRequest

logger = logging.getLogger(__name__)


class ZibalService:
    """
    سرویس برای تعامل با APIهای مختلف زیبال.
    این سرویس شامل متدهایی برای پرداخت، کیف پول، استرداد و گزارش‌گیری است.
    """

    def __init__(self):
        self.access_token = getattr(settings, "ZIBAL_ACCESS_TOKEN", None)
        self.merchant_id = getattr(settings, "ZIBAL_MERCHANT_ID", "zibal")
        self.api_base_url = "https://api.zibal.ir/v1"
        self.gateway_base_url = "https://gateway.zibal.ir/v1"
        self.http_client = HttpClient(service_name='zibal')

    def _get_auth_headers(self):
        if not self.access_token:
            raise ValueError("ZIBAL_ACCESS_TOKEN is not configured in settings.")
        return {"Authorization": f"Bearer {self.access_token}"}

    def _post_request(self, url, payload=None, is_gateway=False):
        base_url = self.gateway_base_url if is_gateway else self.api_base_url
        full_url = f"{base_url}{url}"
        headers = {} if is_gateway else self._get_auth_headers()
        try:
            response = self.http_client.post(full_url, json=payload, headers=headers)
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Request Exception for {full_url}: {e}")
            raise ValidationError("خطا در ارتباط با درگاه پرداخت.") from e

    def _get_request(self, url):
        full_url = f"{self.api_base_url}{url}"
        try:
            response = self.http_client.get(full_url, headers=self._get_auth_headers())
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Request Exception for {full_url}: {e}")
            raise ValidationError("خطا در ارتباط با سرور.") from e

    def create_payment(self, amount, description, callback_url, order_id, mobile=None):
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
        payload = {"merchant": self.merchant_id, "trackId": track_id, "amount": amount}
        return self._post_request("/verify", payload, is_gateway=True)

    def generate_payment_url(self, track_id):
        return f"https://gateway.zibal.ir/start/{track_id}"

    def request_refund(self, track_id, amount):
        payload = {"trackId": track_id, "amount": amount}
        return self._post_request("/refund", payload)


class WalletService:
    def __init__(self, user):
        self.user = user
        self.zibal_service = ZibalService()

    def get_wallet(self):
        try:
            return Wallet.objects.get(user=self.user)
        except Wallet.DoesNotExist:
            raise NotFound("کیف پول برای این کاربر یافت نشد.")

    def create_deposit(self, amount: Decimal, callback_url_builder):
        wallet = self.get_wallet()
        order_id = str(uuid.uuid4())

        transaction = Transaction.objects.create(
            wallet=wallet,
            amount=amount,
            transaction_type=Transaction.TransactionType.DEPOSIT,
            order_id=order_id,
            status=Transaction.Status.PENDING,
            description="شارژ کیف پول",
        )

        callback_url = callback_url_builder("/api/wallet/verify-deposit/")
        mobile_number = (
            f"0{self.user.phone_number.national_number}"
            if self.user.phone_number
            else None
        )

        zibal_response = self.zibal_service.create_payment(
            amount=int(amount),
            description=f"شارژ کیف پول برای سفارش {order_id}",
            callback_url=callback_url,
            order_id=order_id,
            mobile=mobile_number,
        )

        track_id = zibal_response.get("trackId")
        if track_id:
            transaction.authority = str(track_id)
            transaction.save()
            return self.zibal_service.generate_payment_url(track_id)

        transaction.status = Transaction.Status.FAILED
        transaction.description = zibal_response.get(
            "message", "ایجاد پرداخت با شکست مواجه شد."
        )
        transaction.save()
        raise ValidationError(transaction.description)

    @staticmethod
    def verify_and_process_deposit(track_id: str, order_id: str):
        try:
            tx = Transaction.objects.get(order_id=order_id, authority=track_id)
            if tx.status != Transaction.Status.PENDING:
                logger.warning(
                    f"تایید پرداخت برای تراکنش {tx.id} که قبلا پردازش شده، نادیده گرفته شد."
                )
                return
        except Transaction.DoesNotExist:
            logger.error(
                f"تراکنشی برای order_id={order_id} و track_id={track_id} یافت نشد."
            )
            return

        zibal_service = ZibalService()
        verification_response = zibal_service.verify_payment(
            track_id=track_id, amount=int(tx.amount)
        )
        result = verification_response.get("result")

        if result in [100, 201]:  # Success or Already Verified
            try:
                with transaction.atomic():
                    tx_atomic = Transaction.objects.select_for_update().get(id=tx.id)
                    if tx_atomic.status != Transaction.Status.PENDING:
                        return

                    wallet = Wallet.objects.select_for_update().get(id=tx_atomic.wallet.id)
                    wallet.total_balance += tx_atomic.amount
                    wallet.withdrawable_balance += tx_atomic.amount
                    wallet.save()

                    tx_atomic.status = Transaction.Status.SUCCESS
                    tx_atomic.ref_number = verification_response.get("refNumber")
                    tx_atomic.description = verification_response.get("description", "پرداخت موفق")
                    tx_atomic.save()
                logger.info(f"واریز برای تراکنش {tx.id} با موفقیت تایید و پردازش شد.")
            except Exception as e:
                logger.error(f"خطا در پردازش واریز موفق برای تراکنش {tx.id}: {e}")
        else:
            tx.status = Transaction.Status.FAILED
            tx.description = verification_response.get("message", "تایید پرداخت ناموفق بود.")
            tx.save()
            logger.error(f"تایید زیبال برای تراکنش {tx.id} ناموفق بود: {tx.description}")

    def create_withdrawal_request(self, amount: Decimal, card_number: str, sheba_number: str) -> WithdrawalRequest:
        if amount < settings.MINIMUM_WITHDRAWAL_AMOUNT:
            raise ValidationError(
                f"حداقل مقدار برداشت {settings.MINIMUM_WITHDRAWAL_AMOUNT:,.0f} ریال است."
            )

        if WithdrawalRequest.objects.filter(
            user=self.user, created_at__gte=timezone.now() - timedelta(hours=24)
        ).exists():
            raise ValidationError("شما در ۲۴ ساعت گذشته یک درخواست برداشت ثبت کرده‌اید.")

        with transaction.atomic():
            wallet = self.get_wallet()
            wallet_for_update = Wallet.objects.select_for_update().get(user=self.user)

            if wallet_for_update.withdrawable_balance < amount:
                raise ValidationError("موجودی قابل برداشت کافی نیست.")

            if not wallet_for_update.card_number:
                wallet_for_update.card_number = card_number
            if not wallet_for_update.sheba_number:
                wallet_for_update.sheba_number = sheba_number

            wallet_for_update.total_balance -= amount
            wallet_for_update.withdrawable_balance -= amount
            wallet_for_update.save()

            withdrawal_request = WithdrawalRequest.objects.create(user=self.user, amount=amount)
            return withdrawal_request

    @staticmethod
    def approve_withdrawal_request(withdrawal_request: WithdrawalRequest) -> WithdrawalRequest:
        if withdrawal_request.status != WithdrawalRequest.Status.PENDING:
            raise ValidationError(f"درخواست قبلا در وضعیت {withdrawal_request.get_status_display()} بوده است.")

        with transaction.atomic():
            withdrawal_request.status = WithdrawalRequest.Status.APPROVED
            withdrawal_request.save()

            Transaction.objects.create(
                wallet=withdrawal_request.user.wallet,
                amount=withdrawal_request.amount,
                transaction_type=Transaction.TransactionType.WITHDRAWAL,
                status=Transaction.Status.SUCCESS,
                description=f"درخواست برداشت {withdrawal_request.id} توسط ادمین تایید شد.",
            )
        return withdrawal_request

    @staticmethod
    def reject_withdrawal_request(withdrawal_request: WithdrawalRequest) -> WithdrawalRequest:
        if withdrawal_request.status != WithdrawalRequest.Status.PENDING:
            raise ValidationError(f"درخواست قبلا در وضعیت {withdrawal_request.get_status_display()} بوده است.")

        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(user=withdrawal_request.user)
            wallet.total_balance += withdrawal_request.amount
            wallet.withdrawable_balance += withdrawal_request.amount
            wallet.save()

            withdrawal_request.status = WithdrawalRequest.Status.REJECTED
            withdrawal_request.save()
        return withdrawal_request

    @staticmethod
    def process_transaction(user, amount: Decimal, transaction_type: str, description: str = ""):
        wallet = Wallet.objects.get(user=user)
        is_debit = transaction_type in [
            Transaction.TransactionType.WITHDRAWAL,
            Transaction.TransactionType.ENTRY_FEE,
            Transaction.TransactionType.TOKEN_SPENT,
        ]

        with transaction.atomic():
            wallet_for_update = Wallet.objects.select_for_update().get(user=user)

            if is_debit:
                if "token" in transaction_type:
                    if wallet_for_update.token_balance < amount:
                        raise ValidationError("موجودی توکن کافی نیست.")
                    wallet_for_update.token_balance -= amount
                else:
                    if wallet_for_update.withdrawable_balance < amount:
                        raise ValidationError("موجودی قابل برداشت کافی نیست.")
                    wallet_for_update.total_balance -= amount
                    wallet_for_update.withdrawable_balance -= amount
            else: # Credit
                if "token" in transaction_type:
                    wallet_for_update.token_balance += amount
                else:
                    wallet_for_update.total_balance += amount
                    if transaction_type in [Transaction.TransactionType.DEPOSIT, Transaction.TransactionType.PRIZE]:
                        wallet_for_update.withdrawable_balance += amount

            wallet_for_update.save()

            return Transaction.objects.create(
                wallet=wallet,
                amount=amount,
                transaction_type=transaction_type,
                description=description,
                status=Transaction.Status.SUCCESS,
            )

    def create_refund_request(self, track_id: str, amount: Decimal):
        try:
            transaction_to_refund = Transaction.objects.get(
                authority=track_id,
                status=Transaction.Status.SUCCESS,
                wallet__user=self.user
            )
        except Transaction.DoesNotExist:
            raise NotFound("تراکنش موفق با این شناسه یافت نشد.")

        if transaction_to_refund.is_refunded:
            raise ValidationError("این تراکنش قبلا استرداد شده است.")

        refund_amount = amount or transaction_to_refund.amount

        zibal_response = self.zibal_service.request_refund(
            track_id=track_id,
            amount=int(refund_amount)
        )

        if zibal_response.get("result") == 1:
            with transaction.atomic():
                refund_data = zibal_response.get("data", {})
                new_refund = Refund.objects.create(
                    transaction=transaction_to_refund,
                    amount=refund_amount,
                    refund_id=refund_data.get("refundId"),
                    status=Refund.Status.PENDING,
                    description=zibal_response.get("message")
                )
                transaction_to_refund.is_refunded = True
                transaction_to_refund.save()
            return new_refund
        else:
            raise ValidationError(zibal_response.get("message", "خطا در استرداد وجه."))

# This file is intentionally left blank to resolve an ImportError in the tests.
from celery import shared_task
from django.db import transaction
from django.apps import apps
from .services import ZibalService
from .models import Transaction, Wallet
from logging import getLogger

logger = getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def verify_deposit_task(self, track_id, order_id):
    """
    Celery task to verify a deposit transaction with Zibal.
    """
    try:
        with transaction.atomic():
            transaction_obj = Transaction.objects.select_for_update().get(
                order_id=order_id, authority=track_id
            )
            if transaction_obj.status == "success":
                logger.info(
                    f"Transaction with order_id {order_id} has already been verified and processed."
                )
                return f"Transaction {order_id} already processed."

            zibal_service = ZibalService()
            response = zibal_service.verify_payment(
                track_id=track_id, amount=int(transaction_obj.amount)
            )

            if response.get("result") in [100, 201]:
                transaction_obj.status = "success"
                transaction_obj.ref_number = response.get("refNumber")
                transaction_obj.description = response.get(
                    "description", "Payment successful"
                )

                wallet = Wallet.objects.select_for_update().get(
                    id=transaction_obj.wallet_id
                )
                wallet.total_balance += transaction_obj.amount
                wallet.withdrawable_balance += transaction_obj.amount
                wallet.save(update_fields=["total_balance", "withdrawable_balance"])
                transaction_obj.save(update_fields=["status", "ref_number", "description"])

                logger.info(
                    f"Successfully verified and updated wallet for order {order_id}."
                )
                return (
                    f"Verification for order {order_id} completed with status: success"
                )

            else:
                transaction_obj.status = "failed"
                transaction_obj.description = response.get(
                    "message", "Payment verification failed"
                )
                transaction_obj.save(update_fields=["status", "description"])
                logger.warning(
                    f"Payment verification failed for order {order_id}: {transaction_obj.description}"
                )
                return f"Verification for order {order_id} completed with status: failed"

    except Transaction.DoesNotExist:
        logger.error(f"Transaction with order_id {order_id} not found for verification.")
        return f"Transaction with order_id {order_id} not found."
    except Exception as exc:
        logger.error(f"An error occurred during deposit verification for order {order_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)

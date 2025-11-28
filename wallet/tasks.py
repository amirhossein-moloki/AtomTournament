# This file is intentionally left blank to resolve an ImportError in the tests.
from celery import shared_task
from django.apps import apps
from .services import ZibalService
from .models import Transaction
from logging import getLogger

logger = getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def verify_deposit_task(self, track_id, order_id):
    """
    Celery task to verify a deposit transaction with Zibal.
    """
    try:
        transaction = Transaction.objects.get(order_id=order_id, authority=track_id)
        zibal_service = ZibalService()
        response = zibal_service.verify_payment(track_id=track_id, amount=int(transaction.amount))

        if response.get("result") == 100:
            transaction.status = "success"
            transaction.ref_number = response.get("refNumber")
            transaction.description = response.get("description", "Payment successful")

            # Update wallet balance
            wallet = transaction.wallet
            wallet.total_balance += transaction.amount
            wallet.withdrawable_balance += transaction.amount
            wallet.save()

        else:
            transaction.status = "failed"
            transaction.description = response.get("message", "Payment verification failed")

        transaction.save()
        return f"Verification for order {order_id} completed with status: {transaction.status}"

    except Transaction.DoesNotExist:
        logger.error(f"Transaction with order_id {order_id} not found for verification.")
        return f"Transaction with order_id {order_id} not found."
    except Exception as exc:
        logger.error(f"An error occurred during deposit verification for order {order_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)

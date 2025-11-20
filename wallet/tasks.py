from celery import shared_task
from django.db import transaction
import logging

from .services import ZibalService

logger = logging.getLogger(__name__)


@shared_task
def verify_deposit_task(track_id, order_id):
    """
    Celery task to verify a deposit with Zibal and update the wallet.
    """
    from .models import Transaction, Wallet

    try:
        tx = Transaction.objects.get(order_id=order_id, authority=track_id)
    except Transaction.DoesNotExist:
        logger.error(f"Transaction not found for order_id={order_id} and track_id={track_id} in Celery task.")
        return

    if tx.status != "pending":
        logger.warning(f"Verification task running on already processed transaction {tx.id} with status {tx.status}")
        return

    zibal = ZibalService()
    verification_response = zibal.verify_payment(track_id=track_id, amount=int(tx.amount))
    result = verification_response.get("result")

    if result == 100:  # Success
        try:
            with transaction.atomic():
                wallet = Wallet.objects.select_for_update().get(id=tx.wallet.id)
                tx.status = "success"
                tx.ref_number = verification_response.get("refNumber")
                tx.description = verification_response.get("description", "Payment successful")
                wallet.total_balance += tx.amount
                wallet.withdrawable_balance += tx.amount
                wallet.save()
                tx.save()
            logger.info(f"Successfully verified and processed deposit for transaction {tx.id}")
        except Exception as e:
            logger.error(f"Error processing successful deposit for transaction {tx.id} in Celery task: {e}")
            # The transaction remains pending for manual/automatic reconciliation
    elif result == 201:  # Already verified
        logger.warning(f"Zibal reported transaction {tx.id} (trackId: {track_id}) as already verified in Celery task.")
        if tx.status == "pending":
            inquiry_response = zibal.inquiry_payment(track_id=track_id)
            if inquiry_response.get("status") == 1: # Paid and verified
                with transaction.atomic():
                    wallet = Wallet.objects.select_for_update().get(id=tx.wallet.id)
                    wallet.total_balance += tx.amount
                    wallet.withdrawable_balance += tx.amount
                    wallet.save()
                    tx.status = "success"
                    tx.ref_number = inquiry_response.get("refNumber")
                    tx.save()
    else:  # Verification failed
        tx.status = "failed"
        tx.description = verification_response.get("message", "Payment verification failed.")
        tx.save()
        logger.error(f"Zibal verification failed for tx {tx.id} (trackId: {track_id}) in Celery task: {tx.description}")

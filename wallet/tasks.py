from celery import shared_task
from django.db import transaction
import logging

from .services import ZibalService

logger = logging.getLogger(__name__)


@shared_task
def verify_deposit_task(track_id, order_id):
    """
    Celery task to verify a deposit with Zibal and update the wallet.
    This task is designed to be idempotent to prevent duplicate processing.
    """
    from .models import Transaction, Wallet

    try:
        # Initial check to quickly discard tasks for already processed transactions.
        tx = Transaction.objects.get(order_id=order_id, authority=track_id)
        if tx.status != "pending":
            logger.warning(
                f"Verification task skipped for already processed transaction {tx.id} with status {tx.status}"
            )
            return
    except Transaction.DoesNotExist:
        logger.error(
            f"Transaction not found for order_id={order_id} and track_id={track_id} in Celery task."
        )
        return

    zibal = ZibalService()
    verification_response = zibal.verify_payment(
        track_id=track_id, amount=int(tx.amount)
    )
    result = verification_response.get("result")

    # A result of 100 means success.
    # A result of 201 means the transaction was already successfully verified.
    # In both cases, the payment is considered successful from Zibal's end.
    if result in [100, 201]:
        try:
            with transaction.atomic():
                # Re-fetch and lock the transaction and wallet to prevent race conditions.
                tx_inside_atomic = Transaction.objects.select_for_update().get(id=tx.id)

                # Critical check: Ensure the transaction hasn't been processed by another task
                # between the initial check and the start of this atomic block.
                if tx_inside_atomic.status != "pending":
                    logger.warning(
                        f"Transaction {tx.id} was already processed by another worker. Skipping update."
                    )
                    return

                wallet = Wallet.objects.select_for_update().get(
                    id=tx_inside_atomic.wallet.id
                )

                # Update wallet and transaction details
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
            # If any error occurs during the database transaction, it will be rolled back.
            # The transaction status remains 'pending' for a potential retry or manual check.
            logger.error(
                f"Error processing successful deposit for transaction {tx.id} in Celery task: {e}"
            )

    else:  # Verification failed at Zibal
        tx.status = "failed"
        tx.description = verification_response.get(
            "message", "Payment verification failed."
        )
        tx.save()
        logger.error(
            f"Zibal verification failed for tx {tx.id} (trackId: {track_id}) in Celery task: {tx.description}"
        )

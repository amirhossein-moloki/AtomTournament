from django.db.models import F
from django.db.models.signals import post_save
from django.dispatch import receiver

from notifications.tasks import send_email_notification, send_sms_notification
from users.models import User

from .models import Transaction, Wallet


# @receiver(post_save, sender=Transaction)
# def transaction_post_save(sender, instance, created, **kwargs):
#     """
#     NOTE: This signal is disabled.
#     The logic for updating wallet balances has been moved to the
#     `wallet.services.process_transaction` function to prevent race conditions
#     and ensure all balance changes are handled atomically with the
#     transaction creation.
#     """
#     if created:
#         # The following logic is unsafe and has been replaced.
#         # wallet = instance.wallet
#         # if instance.transaction_type in ["deposit", "prize"]:
#         #     wallet.total_balance = F("total_balance") + instance.amount
#         #     wallet.withdrawable_balance = F("withdrawable_balance") + instance.amount
#         # elif instance.transaction_type in ["withdrawal", "entry_fee"]:
#         #     wallet.total_balance = F("total_balance") - instance.amount
#         #     wallet.withdrawable_balance = F("withdrawable_balance") - instance.amount
#         # wallet.save()
#
#         # Notification logic can be moved to the service layer as well.
#         user = instance.wallet.user
#         context = {
#             "transaction_type": instance.get_transaction_type_display(),
#             "amount": instance.amount,
#             "timestamp": instance.timestamp,
#         }
#         if user.email:
#             send_email_notification.delay(user.email, "New Transaction", context)
#         if user.phone_number:
#             send_sms_notification.delay(str(user.phone_number), context)


@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.create(user=instance, token_balance=1000)

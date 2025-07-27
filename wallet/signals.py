from django.db.models.signals import post_save
from django.dispatch import receiver
from notifications.tasks import send_email_notification, send_sms_notification
from .models import Transaction


@receiver(post_save, sender=Transaction)
def send_transaction_notification(sender, instance, created, **kwargs):
    if created:
        user = instance.wallet.user
        context = {
            "transaction_type": instance.get_transaction_type_display(),
            "amount": instance.amount,
            "timestamp": instance.timestamp,
        }
        if user.email:
            send_email_notification.delay(
                user.email, "New Transaction", context
            )
        if user.phone_number:
            send_sms_notification.delay(str(user.phone_number), context)

# support/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from common.tasks import convert_image_to_avif_task
from .models import TicketAttachment

@receiver(post_save, sender=TicketAttachment)
def schedule_avif_conversion(sender, instance, created, **kwargs):
    """
    وقتی یک فایل پیوست تیکت جدید ساخته می‌شود، اگر تصویر بود،
    یک تسک برای تبدیل آن به AVIF ایجاد می‌کنیم.
    """
    if created and instance.file and 'image' in instance.file.file.content_type:
        convert_image_to_avif_task.delay(
            app_label='support',
            model_name='TicketAttachment',
            instance_pk=instance.pk,
            field_name='file'
        )

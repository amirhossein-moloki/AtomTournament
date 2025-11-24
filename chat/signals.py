# chat/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from common.tasks import convert_image_to_avif_task
from .models import Attachment

@receiver(post_save, sender=Attachment)
def schedule_avif_conversion(sender, instance, created, **kwargs):
    """
    وقتی یک فایل پیوست جدید ساخته می‌شود، اگر تصویر بود،
    یک تسک برای تبدیل آن به AVIF ایجاد می‌کنیم.
    """
    if created and instance.file and 'image' in instance.mime:
        convert_image_to_avif_task.delay(
            app_label='chat',
            model_name='Attachment',
            instance_pk=instance.pk,
            field_name='file'
        )

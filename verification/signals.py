# verification/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from common.tasks import convert_image_to_avif_task
from .models import Verification


@receiver(post_save, sender=Verification)
def schedule_avif_conversion(sender, instance, created, **kwargs):
    """
    وقتی یک وریفیکیشن جدید ساخته می‌شود، اگر تصویر داشت،
    یک تسک برای تبدیل آن به AVIF ایجاد می‌کنیم.
    """
    # در صورتی که فایل جدیدی آپلود شده باشد، تسک را اجرا کن
    if instance.id_card_image:
        if created or (kwargs.get('update_fields') and 'id_card_image' in kwargs['update_fields']):
            convert_image_to_avif_task.delay(
                app_label='verification',
                model_name='Verification',
                instance_pk=instance.pk,
                field_name='id_card_image'
            )

    if instance.selfie_image:
        if created or (kwargs.get('update_fields') and 'selfie_image' in kwargs['update_fields']):
            convert_image_to_avif_task.delay(
                app_label='verification',
                model_name='Verification',
                instance_pk=instance.pk,
                field_name='selfie_image'
            )

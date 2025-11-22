from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Attachment
from common.tasks import convert_image_to_webp_task

@receiver(post_save, sender=Attachment)
def schedule_webp_conversion(sender, instance, created, **kwargs):
    """
    بعد از آپلود یک فایل ضمیمه جدید، تسک تبدیل به WebP را زمان‌بندی می‌کند.
    """
    if created and instance.file: # فقط برای فایل‌های جدید
        convert_image_to_webp_task.delay(
            app_label='chat',
            model_name='Attachment',
            instance_pk=instance.pk,
            field_name='file'
        )

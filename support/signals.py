# support/signals.py
from django.conf import settings
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
    if created and instance.file:
        task_kwargs = {
            'app_label': 'support',
            'model_name': 'TicketAttachment',
            'instance_pk': instance.pk,
            'field_name': 'file'
        }
        if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
            # اگر در حالت تست یا توسعه بودیم، تسک را مستقیم اجرا کن
            convert_image_to_avif_task.apply(kwargs=task_kwargs)
        else:
            # در غیر این صورت، آن را در صف Celery قرار بده
            convert_image_to_avif_task.delay(**task_kwargs)

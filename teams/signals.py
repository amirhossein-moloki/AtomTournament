# teams/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from common.tasks import convert_image_to_avif_task
from .models import Team

@receiver(post_save, sender=Team)
def schedule_avif_conversion(sender, instance, created, **kwargs):
    """
    وقتی یک تیم جدید ساخته می‌شود، اگر آواتار داشت،
    یک تسک برای تبدیل آن به AVIF ایجاد می‌کنیم.
    """
    if created and instance.team_picture:
        convert_image_to_avif_task.delay(
            app_label='teams',
            model_name='Team',
            instance_pk=instance.pk,
            field_name='team_picture'
        )

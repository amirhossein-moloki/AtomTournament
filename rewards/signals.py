from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Prize
from common.tasks import convert_image_to_avif_task

@receiver(post_save, sender=Prize)
def schedule_webp_conversion(sender, instance, created, **kwargs):
    """
    After a new Prize is created, schedule AVIF conversion for its image.
    """
    if created and instance.image:
        convert_image_to_avif_task.delay(
            app_label='rewards',
            model_name='Prize',
            instance_pk=instance.pk,
            field_name='image'
        )

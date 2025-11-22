from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Verification
from common.tasks import convert_image_to_webp_task

@receiver(post_save, sender=Verification)
def schedule_webp_conversion(sender, instance, created, **kwargs):
    """
    After a new Verification object is created, schedule WebP conversion tasks.
    """
    if created:
        if instance.id_card_image:
            convert_image_to_webp_task.delay(
                app_label='verification',
                model_name='Verification',
                instance_pk=instance.pk,
                field_name='id_card_image'
            )
        if instance.selfie_image:
            convert_image_to_webp_task.delay(
                app_label='verification',
                model_name='Verification',
                instance_pk=instance.pk,
                field_name='selfie_image'
            )

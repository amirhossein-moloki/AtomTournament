from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import TicketAttachment
from common.tasks import convert_image_to_webp_task

@receiver(post_save, sender=TicketAttachment)
def schedule_webp_conversion(sender, instance, created, **kwargs):
    """
    After a new TicketAttachment is created, schedule WebP conversion.
    """
    if created and instance.file:
        convert_image_to_webp_task.delay(
            app_label='support',
            model_name='TicketAttachment',
            instance_pk=instance.pk,
            field_name='file'
        )

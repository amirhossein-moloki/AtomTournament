from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Team
from common.tasks import convert_image_to_webp_task

@receiver(post_save, sender=Team)
def schedule_webp_conversion(sender, instance, created, **kwargs):
    """
    After a new Team is created, schedule WebP conversion for its picture.
    """
    if created and instance.team_picture:
        convert_image_to_webp_task.delay(
            app_label='teams',
            model_name='Team',
            instance_pk=instance.pk,
            field_name='team_picture'
        )

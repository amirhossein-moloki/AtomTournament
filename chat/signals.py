from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save
from django.dispatch import receiver

from common.tasks import convert_image_to_avif_task

from .models import Attachment


@receiver(post_save, sender=Attachment)
def optimize_image_attachment(sender, instance, created, **kwargs):
    """
    If a new image attachment is created, trigger the AVIF conversion task.
    """
    if created and instance.file:
        # A list of common image extensions
        image_extensions = [".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic"]
        file_name = instance.file.name.lower()

        # Check if the file has an image extension
        if any(file_name.endswith(ext) for ext in image_extensions):
            content_type = ContentType.objects.get_for_model(Attachment)
            convert_image_to_avif_task.delay(
                content_type_pk=content_type.pk, object_id=instance.pk
            )

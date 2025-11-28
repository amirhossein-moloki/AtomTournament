from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import AuthorProfile, Media
from .tasks import convert_media_image_to_avif_task

User = get_user_model()

@receiver(post_save, sender=User)
def create_author_profile(sender, instance, created, **kwargs):
    """
    Automatically create an AuthorProfile for a new User.
    """
    if created:
        AuthorProfile.objects.create(user=instance, display_name=instance.username)


@receiver(post_save, sender=Media)
def queue_media_image_processing(sender, instance, created, **kwargs):
    """
    Queue a Celery task to process and convert the media image to AVIF
    when a new Media object is created.
    """
    if created and 'image' in instance.mime:
        convert_media_image_to_avif_task.delay(instance.id)

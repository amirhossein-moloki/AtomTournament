from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import AuthorProfile

User = get_user_model()

@receiver(post_save, sender=User)
def create_author_profile(sender, instance, created, **kwargs):
    """
    Automatically create an AuthorProfile for a new User.
    """
    if created:
        AuthorProfile.objects.create(user=instance, display_name=instance.username)

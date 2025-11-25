import shortuuid
from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, Role
from common.tasks import convert_image_to_avif_task

@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    """
    Handles post-save operations for User model:
    - Assigns a default role and generates a referral code for new users.
    - Updates the user's rank based on their score.
    - Schedules WebP conversion for a new profile picture.
    """
    if created:
        # Assign default role
        default_role = Role.get_default_role()
        if default_role:
            instance.groups.add(default_role.group)

        # Generate referral code
        if not instance.referral_code:
            instance.referral_code = shortuuid.uuid()
            instance.save(update_fields=['referral_code']) # Save only the necessary field

        # Schedule AVIF conversion for profile picture
        if instance.profile_picture:
            convert_image_to_avif_task.delay(
                app_label='users',
                model_name='User',
                instance_pk=instance.pk,
                field_name='profile_picture'
            )

    # Update rank whenever a user is saved (created or updated)
    # The update_rank method itself handles the logic of whether to save or not
    instance.update_rank()


from django.conf import settings
from django.db import models
from common.fields import OptimizedImageField, OptimizedVideoField


class Verification(models.Model):
    LEVEL_CHOICES = (
        (1, "Level 1"),
        (2, "Level 2"),
        (3, "Level 3"),
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    level = models.IntegerField(choices=LEVEL_CHOICES, default=1)
    id_card_image = OptimizedImageField(
        upload_to="verification_images/", blank=True, null=True
    )
    selfie_image = OptimizedImageField(
        upload_to="verification_images/", blank=True, null=True
    )
    video = OptimizedVideoField(upload_to="verification_videos/", blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - Level {self.level}"

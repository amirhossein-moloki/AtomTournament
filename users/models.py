import shortuuid
from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from django.db.models.signals import post_save
from phonenumber_field.modelfields import PhoneNumberField
from common.fields import OptimizedImageField
from common.utils.files import get_sanitized_upload_path


class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone_number = PhoneNumberField(unique=True)
    profile_picture = OptimizedImageField(
        upload_to=get_sanitized_upload_path, null=True, blank=True
    )
    score = models.IntegerField(default=0)
    rank = models.ForeignKey(
        "tournaments.Rank", on_delete=models.SET_NULL, null=True, blank=True
    )
    referral_code = models.CharField(max_length=22, unique=True, blank=True)
    is_phone_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.username

    @property
    def role(self):
        return [group.name for group in self.groups.all()]

    def update_rank(self):
        from tournaments.models import Rank

        new_rank = (
            Rank.objects.filter(required_score__lte=self.score)
            .order_by("-required_score")
            .first()
        )
        if new_rank and self.rank != new_rank:
            self.rank = new_rank
            self.save()


class Role(models.Model):
    """
    Extends Django's Group model to add a description and a default role.
    """

    group = models.OneToOneField(Group, on_delete=models.CASCADE, related_name="role")
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.group.name

    @staticmethod
    def get_default_role():
        return Role.objects.filter(is_default=True).first()


class Referral(models.Model):
    """
    Stores the relationship between a referrer and a referred user.
    """
    referrer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referrals_made')
    referred = models.OneToOneField(User, on_delete=models.CASCADE, related_name='referred_by')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.referrer.username} referred {self.referred.username}"


class InGameID(models.Model):
    user = models.ForeignKey(
        "User", on_delete=models.CASCADE, related_name="in_game_ids", null=True
    )
    game = models.ForeignKey("tournaments.Game", on_delete=models.CASCADE)
    player_id = models.CharField(max_length=100)

    class Meta:
        unique_together = ("user", "game")


from django.utils import timezone
from datetime import timedelta

from django.utils import timezone
from datetime import timedelta

class OTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    identifier = models.CharField(max_length=255)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.identifier} - {self.code}"

    def save(self, *args, **kwargs):
        if not self.pk:
            self.expires_at = timezone.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

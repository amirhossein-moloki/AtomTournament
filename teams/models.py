from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from common.fields import OptimizedImageField
from common.utils.files import get_sanitized_upload_path


class Team(models.Model):
    name = models.CharField(max_length=100)
    captain = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="captained_teams"
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through="TeamMembership", related_name="teams"
    )
    team_picture = OptimizedImageField(upload_to=get_sanitized_upload_path, null=True, blank=True)
    max_members = models.PositiveIntegerField(default=5)

    def __str__(self):
        return self.name


def validate_user_team_limit(user):
    if user.teams.count() >= 10:
        raise ValidationError("A user cannot be in more than 10 teams.")


class TeamMembership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    team = models.ForeignKey("Team", on_delete=models.CASCADE)
    date_joined = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "team")

    def save(self, *args, **kwargs):
        validate_user_team_limit(self.user)
        if self.team.members.count() >= self.team.max_members:
            raise ValidationError("This team is already full.")
        super().save(*args, **kwargs)


class TeamInvitation(models.Model):
    INVITATION_STATUS_CHOICES = (
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
    )
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_invitations"
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_invitations"
    )
    team = models.ForeignKey("Team", on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20, choices=INVITATION_STATUS_CHOICES, default="pending"
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("from_user", "to_user", "team")

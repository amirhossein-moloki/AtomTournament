from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from django.db.models.signals import post_save
from phonenumber_field.modelfields import PhoneNumberField


class User(AbstractUser):
    phone_number = PhoneNumberField(unique=True)
    profile_picture = models.ImageField(
        upload_to="profile_pictures/", null=True, blank=True
    )
    points = models.IntegerField(default=0)
    authentication_level = models.IntegerField(default=1)
    tournaments_played = models.IntegerField(default=0)

    class Meta:
        app_label = "users"

    def __str__(self):
        return self.username

    @property
    def role(self):
        return [group.name for group in self.groups.all()]


class Role(models.Model):
    """
    Extends Django's Group model to add a description and a default role.
    """

    group = models.OneToOneField(Group, on_delete=models.CASCADE, related_name="role")
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        app_label = "users"

    def __str__(self):
        return self.group.name

    @staticmethod
    def get_default_role():
        return Role.objects.filter(is_default=True).first()


def assign_default_role(sender, instance, created, **kwargs):
    if created:
        default_role = Role.get_default_role()
        if default_role:
            instance.groups.add(default_role.group)


post_save.connect(assign_default_role, sender=User)


class InGameID(models.Model):
    user = models.ForeignKey(
        "User", on_delete=models.CASCADE, related_name="in_game_ids", null=True
    )
    game = models.ForeignKey("tournaments.Game", on_delete=models.CASCADE)
    player_id = models.CharField(max_length=100)

    class Meta:
        unique_together = ("user", "game")
        app_label = "users"


from django.core.exceptions import ValidationError


class Team(models.Model):
    name = models.CharField(max_length=100)
    captain = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="captained_teams"
    )
    members = models.ManyToManyField(User, through="TeamMembership", related_name="teams")
    team_picture = models.ImageField(upload_to="team_pictures/", null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        app_label = "users"


def validate_user_team_limit(user):
    if user.teams.count() >= 10:
        raise ValidationError("A user cannot be in more than 10 teams.")


class TeamMembership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    date_joined = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "team")
        app_label = "users"

    def save(self, *args, **kwargs):
        validate_user_team_limit(self.user)
        super().save(*args, **kwargs)


class TeamInvitation(models.Model):
    INVITATION_STATUS_CHOICES = (
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
    )
    from_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sent_invitations"
    )
    to_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="received_invitations"
    )
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20, choices=INVITATION_STATUS_CHOICES, default="pending"
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("from_user", "to_user", "team")
        app_label = "users"


class OTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} - {self.code}"

    class Meta:
        app_label = "users"

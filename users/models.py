import shortuuid
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from phonenumber_field.modelfields import PhoneNumberField

from blog.models import Role as BlogRole


class User(AbstractUser):
    phone_number = PhoneNumberField(unique=True)
    profile_picture = models.ImageField(
        upload_to="profile_pictures/", null=True, blank=True
    )
    score = models.IntegerField(default=0)
    rank = models.ForeignKey(
        "tournaments.Rank", on_delete=models.SET_NULL, null=True, blank=True
    )
    referral_code = models.CharField(max_length=22, unique=True, blank=True)
    is_phone_verified = models.BooleanField(default=False)
    roles = models.ManyToManyField(BlogRole, blank=True, related_name="users")

    def __str__(self):
        return self.username

    @property
    def role(self):
        return [role.name for role in self.roles.all()]

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


def assign_default_role_and_referral_code(sender, instance, created, **kwargs):
    """
    Assigns a default role and generates a referral code for new users.
    """
    if created:
        # Generate referral code
        if not instance.referral_code:
            instance.referral_code = shortuuid.uuid()
            instance.save()


post_save.connect(assign_default_role_and_referral_code, sender=User)


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


class Team(models.Model):
    name = models.CharField(max_length=100)
    captain = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="captained_teams"
    )
    members = models.ManyToManyField(
        User, through="TeamMembership", related_name="teams"
    )
    team_picture = models.ImageField(upload_to="team_pictures/", null=True, blank=True)
    max_members = models.PositiveIntegerField(default=5)

    def __str__(self):
        return self.name


def validate_user_team_limit(user):
    if user.teams.count() >= 10:
        raise ValidationError("A user cannot be in more than 10 teams.")


class TeamMembership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
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


class OTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} - {self.code}"

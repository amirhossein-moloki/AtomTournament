from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from django.db.models.signals import post_save
from phonenumber_field.modelfields import PhoneNumberField


class User(AbstractUser):
    phone_number = PhoneNumberField(unique=True)

    def __str__(self):
        return self.username


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


class Team(models.Model):
    name = models.CharField(max_length=100)
    captain = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="captained_teams"
    )
    members = models.ManyToManyField(User, related_name="teams")

    def __str__(self):
        return self.name

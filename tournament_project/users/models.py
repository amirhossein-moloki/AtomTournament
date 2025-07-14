from django.contrib.auth.models import AbstractUser
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('tournament_manager', 'Tournament Manager'),
        ('support', 'Support'),
        ('user', 'User'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    phone_number = PhoneNumberField(unique=False)

    def __str__(self):
        return self.username

class InGameID(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='in_game_ids', null=True)
    game = models.ForeignKey('tournaments.Game', on_delete=models.CASCADE)
    player_id = models.CharField(max_length=100)

    class Meta:
        unique_together = ('user', 'game')

class Team(models.Model):
    name = models.CharField(max_length=100)
    captain = models.ForeignKey(User, on_delete=models.PROTECT, related_name='captained_teams')
    members = models.ManyToManyField(User, related_name='teams')

    def __str__(self):
        return self.name

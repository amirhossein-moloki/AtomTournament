from django.db import models
from users.models import User, Team
from django.core.exceptions import ValidationError

class Game(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return self.name

class Tournament(models.Model):
    TOURNAMENT_TYPE_CHOICES = (
        ('individual', 'Individual'),
        ('team', 'Team'),
    )
    type = models.CharField(max_length=20, choices=TOURNAMENT_TYPE_CHOICES, default='individual')
    name = models.CharField(max_length=100)
    game = models.ForeignKey(Game, on_delete=models.PROTECT)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_free = models.BooleanField(default=True)
    entry_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    rules = models.TextField(blank=True)
    participants = models.ManyToManyField(User, related_name='tournaments', blank=True)
    teams = models.ManyToManyField(Team, related_name='tournaments', blank=True)

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError("End date must be after start date.")
        if not self.is_free and (self.entry_fee is None or self.entry_fee <= 0):
            raise ValidationError("Entry fee must be a positive value for paid tournaments.")
        if self.is_free and self.entry_fee is not None and self.entry_fee > 0:
            raise ValidationError("Free tournaments cannot have an entry fee.")
        if self.type == 'individual' and self.teams.exists():
            raise ValidationError("Individual tournaments cannot have team participants.")
        if self.type == 'team' and self.participants.exists():
            raise ValidationError("Team tournaments cannot have individual participants.")

    def __str__(self):
        return self.name

class Match(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='matches')
    round = models.IntegerField()
    participants = models.ManyToManyField(User, related_name='matches', blank=True)
    teams = models.ManyToManyField(Team, related_name='matches', blank=True)
    winner_user = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='won_matches', null=True, blank=True)
    winner_team = models.ForeignKey(Team, on_delete=models.SET_NULL, related_name='won_matches', null=True, blank=True)
    result_proof = models.ImageField(upload_to='result_proofs/', null=True, blank=True)
    is_confirmed = models.BooleanField(default=False)
    is_disputed = models.BooleanField(default=False)

    def clean(self):
        super().clean()
        if self.tournament.type == 'individual' and self.teams.exists():
            raise ValidationError("Individual matches cannot have team participants.")
        if self.tournament.type == 'team' and self.participants.exists():
            raise ValidationError("Team matches cannot have individual participants.")

    def __str__(self):
        if self.tournament.type == 'individual':
            return f'Match in {self.tournament}'
        else:
            return f'Match in {self.tournament}'

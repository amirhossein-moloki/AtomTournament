from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from users.models import User, Team

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
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_free = models.BooleanField(default=True)
    entry_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    rules = models.TextField(blank=True)
    participants = models.ManyToManyField(User, related_name='tournaments', blank=True)
    teams = models.ManyToManyField(Team, related_name='tournaments', blank=True)


    def __str__(self):
        return self.name

class Match(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    round = models.IntegerField()

    # Using GenericForeignKey to allow participants to be either a User or a Team
    participant1_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='participant1', null=True)
    participant1_object_id = models.PositiveIntegerField(null=True)
    participant1 = GenericForeignKey('participant1_content_type', 'participant1_object_id')

    participant2_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='participant2', null=True)
    participant2_object_id = models.PositiveIntegerField(null=True)
    participant2 = GenericForeignKey('participant2_content_type', 'participant2_object_id')

    winner_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True, related_name='winner')
    winner_object_id = models.PositiveIntegerField(null=True, blank=True)
    winner = GenericForeignKey('winner_content_type', 'winner_object_id')

    result_proof = models.ImageField(upload_to='result_proofs/', null=True, blank=True)
    is_confirmed = models.BooleanField(default=False)
    is_disputed = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.participant1} vs {self.participant2} - Tournament: {self.tournament}'

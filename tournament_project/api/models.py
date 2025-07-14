from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('tournament_manager', 'Tournament Manager'),
        ('support', 'Support'),
        ('user', 'User'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    phone_number = models.CharField(max_length=15, unique=True)

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    in_game_ids = models.JSONField(default=dict)

    def __str__(self):
        return self.user.username

class Game(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return self.name

class Team(models.Model):
    name = models.CharField(max_length=100)
    captain = models.ForeignKey(User, on_delete=models.CASCADE, related_name='captained_teams')
    members = models.ManyToManyField(User, related_name='teams')

    def __str__(self):
        return self.name

class Tournament(models.Model):
    FORMAT_CHOICES = (
        ('1v1', '1v1'),
        ('2v2', '2v2'),
        ('5v5', '5v5'),
        ('50v50', '50v50'),
        ('solo', 'Solo'),
        ('duo', 'Duo'),
        ('squad', 'Squad'),
    )
    name = models.CharField(max_length=100)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_free = models.BooleanField(default=True)
    entry_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    rules = models.TextField()
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES)
    participants = models.ManyToManyField(User, related_name='tournaments', blank=True)
    teams = models.ManyToManyField(Team, related_name='tournaments', blank=True)


    def __str__(self):
        return self.name

class Match(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    round = models.IntegerField()
    team1 = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='team1_matches')
    team2 = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='team2_matches')
    winner = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='won_matches', null=True, blank=True)
    result_proof = models.ImageField(upload_to='result_proofs/', null=True, blank=True)
    is_confirmed = models.BooleanField(default=False)
    is_disputed = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.team1} vs {self.team2} - Tournament: {self.tournament}'

class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    total_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    withdrawable_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f'{self.user.username} Wallet'

class Transaction(models.Model):
    TRANSACTION_TYPE_CHOICES = (
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('entry_fee', 'Entry Fee'),
        ('prize', 'Prize'),
    )
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.wallet.user.username} - {self.transaction_type} - {self.amount}'

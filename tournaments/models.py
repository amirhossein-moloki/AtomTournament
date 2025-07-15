from django.core.exceptions import ValidationError
from django.db import models
from users.models import Team, User


class Game(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return self.name


class Tournament(models.Model):
    TOURNAMENT_TYPE_CHOICES = (
        ("individual", "Individual"),
        ("team", "Team"),
    )
    type = models.CharField(
        max_length=20, choices=TOURNAMENT_TYPE_CHOICES, default="individual"
    )
    name = models.CharField(max_length=100)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_free = models.BooleanField(default=True)
    entry_fee = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    rules = models.TextField(blank=True)
    participants = models.ManyToManyField(
        User, through="Participant", related_name="tournaments", blank=True
    )
    teams = models.ManyToManyField(Team, related_name="tournaments", blank=True)

    def clean(self):
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError("End date must be after start date.")
        if not self.is_free and self.entry_fee is None:
            raise ValidationError("Entry fee must be set for paid tournaments.")
        if self.type == "individual" and self.teams.exists():
            raise ValidationError(
                "Individual tournaments cannot have team participants."
            )
        if self.type == "team" and self.participants.exists():
            raise ValidationError(
                "Team tournaments cannot have individual participants."
            )

    def __str__(self):
        return self.name


class Participant(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20,
        choices=(
            ("registered", "Registered"),
            ("checked_in", "Checked-in"),
            ("eliminated", "Eliminated"),
        ),
        default="registered",
    )

    class Meta:
        unique_together = ("user", "tournament")


class Match(models.Model):
    MATCH_TYPE_CHOICES = (
        ("individual", "Individual"),
        ("team", "Team"),
    )
    tournament = models.ForeignKey(
        Tournament, on_delete=models.CASCADE, related_name="matches"
    )
    match_type = models.CharField(
        max_length=20, choices=MATCH_TYPE_CHOICES, default="individual"
    )
    round = models.IntegerField()
    participant1_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="matches_as_participant1",
        null=True,
        blank=True,
    )
    participant2_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="matches_as_participant2",
        null=True,
        blank=True,
    )
    participant1_team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="matches_as_participant1",
        null=True,
        blank=True,
    )
    participant2_team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="matches_as_participant2",
        null=True,
        blank=True,
    )
    winner_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="won_matches",
        null=True,
        blank=True,
    )
    winner_team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="won_matches",
        null=True,
        blank=True,
    )
    result_proof = models.ImageField(
        upload_to="private_result_proofs/", null=True, blank=True
    )
    is_confirmed = models.BooleanField(default=False)
    is_disputed = models.BooleanField(default=False)

    def clean(self):
        if self.match_type == "individual":
            if self.participant1_team or self.participant2_team:
                raise ValidationError(
                    "Individual matches cannot have team participants."
                )
            if not self.participant1_user or not self.participant2_user:
                raise ValidationError("Individual matches must have user participants.")
        elif self.match_type == "team":
            if self.participant1_user or self.participant2_user:
                raise ValidationError("Team matches cannot have user participants.")
            if not self.participant1_team or not self.participant2_team:
                raise ValidationError("Team matches must have team participants.")

    def __str__(self):
        if self.match_type == "individual":
            return f"{self.participant1_user} vs {self.participant2_user} - Tournament: {self.tournament}"
        else:
            return f"{self.participant1_team} vs {self.participant2_team} - Tournament: {self.tournament}"

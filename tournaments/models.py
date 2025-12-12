from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from common.fields import OptimizedImageField, OptimizedVideoField
from common.utils.files import get_sanitized_upload_path


class Rank(models.Model):
    name = models.CharField(max_length=100)
    image = OptimizedImageField(upload_to=get_sanitized_upload_path)
    required_score = models.IntegerField()

    def __str__(self):
        return self.name


class Game(models.Model):
    STATUS_CHOICES = (
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("coming_soon", "Coming Soon"),
    )
    name = models.CharField(max_length=100)
    description = models.TextField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="active", db_index=True
    )

    def __str__(self):
        return self.name


class GameManager(models.Model):
    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="managed_games"
    )
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="managers")

    class Meta:
        unique_together = ("user", "game")
        verbose_name = "Game Manager"
        verbose_name_plural = "Game Managers"

    def __str__(self):
        return f"{self.user.username} is a manager for {self.game.name}"


class Scoring(models.Model):
    tournament = models.ForeignKey("Tournament", on_delete=models.CASCADE)
    user = models.ForeignKey("users.User", on_delete=models.CASCADE)
    score = models.IntegerField()

    class Meta:
        unique_together = ("tournament", "user")


class GameImage(models.Model):
    IMAGE_TYPE_CHOICES = (
        ("hero_banner", "Hero Banner"),
        ("cta_banner", "CTA Banner"),
        ("game_image", "Game Image"),
        ("thumbnail", "Thumbnail"),
        ("icon", "Icon"),
        ("slider", "Slider"),
        ("illustration", "Illustration"),
        ("promotional_banner", "Promotional Banner"),
    )
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="images")
    image_type = models.CharField(max_length=20, choices=IMAGE_TYPE_CHOICES)
    image = OptimizedImageField(upload_to=get_sanitized_upload_path)

    def __str__(self):
        return f"{self.game.name} - {self.get_image_type_display()}"


class TournamentImage(models.Model):
    name = models.CharField(max_length=100, unique=True)
    image = OptimizedImageField(upload_to=get_sanitized_upload_path)

    def __str__(self):
        return self.name


class TournamentColor(models.Model):
    name = models.CharField(max_length=100, unique=True)
    rgb_code = models.CharField(max_length=11)  # e.g., "255,0,0"

    def __str__(self):
        return self.name


class Tournament(models.Model):
    TOURNAMENT_TYPE_CHOICES = (
        ("individual", "Individual"),
        ("team", "Team"),
    )
    TOURNAMENT_MODE_CHOICES = (
        ("team_deathmatch", "Team Deathmatch"),
        ("battle_royale", "Battle Royale"),
    )
    type = models.CharField(
        max_length=20, choices=TOURNAMENT_TYPE_CHOICES, default="individual"
    )
    mode = models.CharField(
        max_length=20,
        choices=TOURNAMENT_MODE_CHOICES,
        default="team_deathmatch",
    )
    max_participants = models.PositiveIntegerField(default=100)
    winner_slots = models.PositiveSmallIntegerField(
        default=5,
        help_text=(
            "Maximum number of winners eligible for rewards. Set to 1 for"
            " champion-only payouts."
        ),
    )
    team_size = models.PositiveIntegerField(default=1)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    image = models.ForeignKey(
        TournamentImage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tournaments",
    )
    color = models.ForeignKey(
        TournamentColor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tournaments",
    )
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    start_date = models.DateTimeField(db_index=True)
    end_date = models.DateTimeField(db_index=True)
    is_free = models.BooleanField(default=True)
    is_token_based = models.BooleanField(default=False)
    entry_fee = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    prize_pool = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total prize pool in Rial.",
    )
    rules = models.TextField(blank=True)
    participants = models.ManyToManyField(
        "users.User", through="Participant", related_name="tournaments", blank=True
    )
    teams = models.ManyToManyField("teams.Team", related_name="tournaments", blank=True)
    creator = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="created_tournaments",
        null=True,
        blank=True,
    )
    countdown_start_time = models.DateTimeField(null=True, blank=True)
    required_verification_level = models.IntegerField(default=1)
    min_rank = models.ForeignKey(
        Rank,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="min_rank_tournaments",
    )
    max_rank = models.ForeignKey(
        Rank,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="max_rank_tournaments",
    )
    top_players = models.ManyToManyField(
        "users.User", related_name="top_placements", blank=True
    )
    top_teams = models.ManyToManyField(
        "teams.Team", related_name="top_placements", blank=True
    )

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError("End date must be after start date.")
        if not self.is_free and self.entry_fee is None:
            raise ValidationError("Entry fee must be set for paid tournaments.")
        if self.pk is not None:
            if self.type == "individual" and self.teams.exists():
                raise ValidationError(
                    "Individual tournaments cannot have team participants."
                )
            if self.type == "team" and self.participants.exists():
                raise ValidationError(
                    "Team tournaments cannot have individual participants."
                )
        if self.type == "individual" and self.team_size != 1:
            raise ValidationError("Individual tournaments must have a team size of 1.")
        if self.type == "team" and self.team_size <= 1:
            raise ValidationError("Team tournaments must have a team size greater than 1.")

    def __str__(self):
        return self.name

    @property
    def status(self):
        now = timezone.now()
        if self.start_date > now:
            return "Upcoming"
        elif self.start_date <= now < self.end_date:
            return "Ongoing"
        else:
            return "Finished"


class Participant(models.Model):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20,
        choices=(
            ("registered", "Registered"),
            ("checked_in", "Checked-in"),
            ("eliminated", "Eliminated"),
        ),
        default="registered",
        db_index=True,
    )
    rank = models.IntegerField(null=True, blank=True)
    prize = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ("user", "tournament")


class Match(models.Model):
    MATCH_TYPE_CHOICES = (
        ("individual", "Individual"),
        ("team", "Team"),
    )
    MATCH_STATUS_CHOICES = (
        ("pending", "Pending"),
        ("ongoing", "Ongoing"),
        ("pending_confirmation", "Pending Confirmation"),
        ("completed", "Completed"),
        ("disputed", "Disputed"),
    )

    tournament = models.ForeignKey(
        Tournament, on_delete=models.CASCADE, related_name="matches"
    )
    match_type = models.CharField(
        max_length=20, choices=MATCH_TYPE_CHOICES, default="individual"
    )
    status = models.CharField(
        max_length=20, choices=MATCH_STATUS_CHOICES, default="pending", db_index=True
    )
    round = models.IntegerField()
    participant1_user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="matches_as_participant1",
        null=True,
        blank=True,
    )
    participant2_user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="matches_as_participant2",
        null=True,
        blank=True,
    )
    participant1_team = models.ForeignKey(
        "teams.Team",
        on_delete=models.CASCADE,
        related_name="matches_as_participant1",
        null=True,
        blank=True,
    )
    participant2_team = models.ForeignKey(
        "teams.Team",
        on_delete=models.CASCADE,
        related_name="matches_as_participant2",
        null=True,
        blank=True,
    )
    winner_user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="won_matches",
        null=True,
        blank=True,
    )
    winner_team = models.ForeignKey(
        "teams.Team",
        on_delete=models.CASCADE,
        related_name="won_matches",
        null=True,
        blank=True,
    )
    result_submitted_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        related_name="submitted_match_results",
        null=True,
        blank=True,
    )
    result_proof = OptimizedImageField(
        upload_to=get_sanitized_upload_path, null=True, blank=True
    )
    is_confirmed = models.BooleanField(default=False)
    is_disputed = models.BooleanField(default=False)
    dispute_reason = models.TextField(blank=True)
    room_id = models.CharField(max_length=100, blank=True)
    password = models.CharField(max_length=100, blank=True)

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

    def is_participant(self, user):
        if self.match_type == "individual":
            return user in [self.participant1_user, self.participant2_user]
        else:
            return (
                user in self.participant1_team.members.all()
                or user in self.participant2_team.members.all()
            )

    def __str__(self):
        if self.match_type == "individual":
            return f"{self.participant1_user} vs {self.participant2_user} - Tournament: {self.tournament}"
        else:
            return f"{self.participant1_team} vs {self.participant2_team} - Tournament: {self.tournament}"


class Report(models.Model):
    REPORT_STATUS_CHOICES = (
        ("pending", "Pending"),
        ("resolved", "Resolved"),
        ("rejected", "Rejected"),
    )
    reporter = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="sent_reports"
    )
    reported_user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="received_reports"
    )
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    match = models.ForeignKey(Match, on_delete=models.CASCADE, null=True, blank=True)
    description = models.TextField()
    evidence = OptimizedImageField(upload_to=get_sanitized_upload_path, null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=REPORT_STATUS_CHOICES, default="pending", db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        location = self.match if self.match else self.tournament
        return (
            f"Report by {self.reporter.username} against {self.reported_user.username}"
            f" in {location}"
        )


class WinnerSubmission(models.Model):
    SUBMISSION_STATUS_CHOICES = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )
    winner = models.ForeignKey("users.User", on_delete=models.CASCADE)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    image = OptimizedImageField(upload_to="winner_submissions/", null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=SUBMISSION_STATUS_CHOICES, default="pending"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Submission by {self.winner.username} for {self.tournament.name}"

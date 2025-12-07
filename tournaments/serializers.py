from django.utils import timezone
from rest_framework import serializers

from teams.serializers import TeamSerializer
from users.models import InGameID, User
from users.serializers import UserReadOnlySerializer
from common.validators import validate_file

from .models import (Game, GameImage, GameManager, Match, Participant, Rank,
                     Report, Scoring, Tournament, TournamentColor,
                     TournamentImage, WinnerSubmission)


class GameImageSerializer(serializers.ModelSerializer):
    """Serializer for the GameImage model."""

    class Meta:
        model = GameImage
        fields = ("game", "image_type", "image")


class TournamentImageSerializer(serializers.ModelSerializer):
    """Serializer for the TournamentImage model."""
    url = serializers.ImageField(source='image', read_only=True)

    class Meta:
        model = TournamentImage
        fields = ("id", "name", "image", "url")


class TournamentColorSerializer(serializers.ModelSerializer):
    """Serializer for the TournamentColor model."""

    class Meta:
        model = TournamentColor
        fields = ("id", "name", "rgb_code")


class GameCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating games."""

    class Meta:
        model = Game
        fields = ("name", "description", "status")


class GameReadOnlySerializer(serializers.ModelSerializer):
    """Serializer for the Game model (read-only)."""

    images = GameImageSerializer(many=True, read_only=True)
    tournaments_count = serializers.SerializerMethodField()
    held_tournaments_count = serializers.IntegerField(read_only=True)
    active_tournaments_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Game
        fields = (
            "id",
            "name",
            "description",
            "images",
            "status",
            "tournaments_count",
            "held_tournaments_count",
            "active_tournaments_count",
        )
        read_only_fields = fields

    def get_tournaments_count(self, obj):
        return {
            "held": obj.held_tournaments_count,
            "active": obj.active_tournaments_count,
        }


class TournamentCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating tournaments."""

    class Meta:
        model = Tournament
        fields = (
            "name",
            "description",
            "image",
            "color",
            "game",
            "start_date",
            "end_date",
            "is_free",
            "entry_fee",
            "prize_pool",
            "rules",
            "type",
            "winner_slots",
            "required_verification_level",
            "min_rank",
            "max_rank",
            "max_participants",
            "team_size",
            "mode",
        )


class TournamentReadOnlySerializer(serializers.ModelSerializer):
    """Serializer for reading tournament data."""

    def __init__(self, *args, **kwargs):
        fields = kwargs.pop("fields", None)

        super().__init__(*args, **kwargs)

        if fields:
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)

    image = TournamentImageSerializer(read_only=True)
    color = TournamentColorSerializer(read_only=True)
    participants = UserReadOnlySerializer(many=True, read_only=True)
    teams = TeamSerializer(many=True, read_only=True)
    game = GameReadOnlySerializer(read_only=True)
    creator = UserReadOnlySerializer(read_only=True)

    final_rank = serializers.IntegerField(read_only=True, allow_null=True)
    prize_won = serializers.DecimalField(
        read_only=True, max_digits=10, decimal_places=2, allow_null=True
    )
    spots_left = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = Tournament
        fields = (
            "id",
            "name",
            "description",
            "image",
            "color",
            "game",
            "start_date",
            "end_date",
            "is_free",
            "entry_fee",
            "prize_pool",
            "rules",
            "type",
            "participants",
            "teams",
            "creator",
            "winner_slots",
            "final_rank",
            "prize_won",
            "countdown_start_time",
            "required_verification_level",
            "min_rank",
            "max_rank",
            "top_players",
            "top_teams",
            "max_participants",
            "team_size",
            "mode",
            "spots_left",
        )
        read_only_fields = fields

    def to_representation(self, instance):
        """
        Conditionally remove fields based on the tournament's status.
        """
        data = super().to_representation(instance)
        status = instance.status

        registration_fields = [
            "spots_left",
            "countdown_start_time",
            "required_verification_level",
            "min_rank",
            "max_rank",
        ]
        result_fields = [
            "final_rank",
            "prize_won",
            "top_players",
            "top_teams",
        ]

        if status == "Finished":
            for field in registration_fields:
                data.pop(field, None)
        elif status == "Ongoing":
            for field in registration_fields + result_fields:
                data.pop(field, None)
        elif status == "Upcoming":
            for field in result_fields:
                data.pop(field, None)

        return data


class TournamentListSerializer(TournamentReadOnlySerializer):
    """
    A lightweight serializer for listing tournaments, showing only essential fields.
    """

    start_countdown = serializers.DateTimeField(
        source="countdown_start_time", read_only=True
    )

    class Meta(TournamentReadOnlySerializer.Meta):
        fields = (
            "id",
            "name",
            "description",
            "image",
            "game",
            "start_date",
            "end_date",
            "start_countdown",
            "is_free",
            "entry_fee",
            "prize_pool",
            "type",
            "spots_left",
        )


class MatchCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating matches (admin only)."""

    class Meta:
        model = Match
        fields = (
            "tournament",
            "round",
            "match_type",
            "participant1_user",
            "participant2_user",
            "participant1_team",
            "participant2_team",
            "room_id",
            "password",
        )
        extra_kwargs = {"password": {"write_only": True}}


class MatchUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a match with a result proof."""

    result_proof = serializers.ImageField(
        required=True,
        validators=[validate_file],
    )

    class Meta:
        model = Match
        fields = ("result_proof",)


class MatchSubmitResultSerializer(serializers.Serializer):
    """Serializer for submitting a match result."""
    winner_id = serializers.IntegerField(required=True)
    result_proof = serializers.ImageField(
        required=True,
        validators=[validate_file],
    )


class MatchReadOnlySerializer(serializers.ModelSerializer):
    """Serializer for reading match data."""

    participant1_user = UserReadOnlySerializer(read_only=True)
    participant2_user = UserReadOnlySerializer(read_only=True)
    participant1_team = TeamSerializer(read_only=True)
    participant2_team = TeamSerializer(read_only=True)
    winner_user = UserReadOnlySerializer(read_only=True)
    winner_team = TeamSerializer(read_only=True)

    class Meta:
        model = Match
        fields = (
            "id",
            "tournament",
            "round",
            "match_type",
            "participant1_user",
            "participant2_user",
            "participant1_team",
            "participant2_team",
            "winner_user",
            "winner_team",
            "result_proof",
            "status",
            "result_submitted_by",
            "is_confirmed",
            "is_disputed",
            "dispute_reason",
            "room_id",
        )
        read_only_fields = fields


class ParticipantSerializer(serializers.ModelSerializer):
    """Serializer for the Participant model."""

    username = serializers.CharField(source="user.username", read_only=True)
    display_picture = serializers.CharField(source="display_picture_url", read_only=True)

    class Meta:
        model = Participant
        fields = (
            "user",
            "tournament",
            "username",
            "status",
            "rank",
            "prize",
            "display_picture",
        )


class ReportSerializer(serializers.ModelSerializer):
    """Serializer for the Report model."""

    reported_user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False
    )
    tournament = serializers.PrimaryKeyRelatedField(
        queryset=Tournament.objects.all(), required=False, allow_null=True
    )
    match = serializers.PrimaryKeyRelatedField(
        queryset=Match.objects.all(), required=False, allow_null=True
    )
    reported_player_id = serializers.CharField(
        write_only=True, required=False, allow_blank=False
    )

    class Meta:
        model = Report
        fields = (
            "id",
            "reporter",
            "reported_user",
            "tournament",
            "match",
            "description",
            "evidence",
            "status",
            "created_at",
            "reported_player_id",
        )
        read_only_fields = ("id", "reporter", "status", "created_at")

    def validate(self, attrs):
        attrs = super().validate(attrs)

        reported_user = attrs.get("reported_user")
        reported_player_id = attrs.pop("reported_player_id", None)
        tournament = attrs.get("tournament")
        match = attrs.get("match")

        if not tournament and not match:
            raise serializers.ValidationError(
                {"tournament": "Tournament is required when match is not provided."}
            )

        if match and tournament:
            if match.tournament_id != tournament.id:
                raise serializers.ValidationError(
                    {"match": "Match does not belong to the provided tournament."}
                )

        if match and not tournament:
            attrs["tournament"] = match.tournament

        tournament = attrs.get("tournament")

        if not reported_user and not reported_player_id:
            raise serializers.ValidationError(
                {"reported_user": "reported_user or reported_player_id is required."}
            )

        if reported_user and reported_player_id:
            raise serializers.ValidationError(
                "Provide only one of reported_user or reported_player_id."
            )

        if reported_player_id:
            if not tournament:
                raise serializers.ValidationError(
                    {"tournament": "Tournament is required when using reported_player_id."}
                )

            try:
                ingame_id = InGameID.objects.get(
                    game=tournament.game, player_id=reported_player_id
                )
            except InGameID.DoesNotExist:
                raise serializers.ValidationError(
                    {
                        "reported_player_id": "No user found with this in-game ID for the tournament's game.",
                    }
                )

            attrs["reported_user"] = ingame_id.user

        return attrs


class WinnerSubmissionSerializer(serializers.ModelSerializer):
    """Serializer for the WinnerSubmission model."""

    class Meta:
        model = WinnerSubmission
        fields = (
            "id",
            "winner",
            "tournament",
            "video",
            "status",
            "created_at",
        )
        read_only_fields = ("id", "winner", "status", "created_at")


class WinnerSubmissionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a WinnerSubmission."""

    video = serializers.FileField(validators=[validate_file])
    tournament = serializers.PrimaryKeyRelatedField(queryset=Tournament.objects.all())

    class Meta:
        model = WinnerSubmission
        fields = ("video", "tournament")


class ScoringSerializer(serializers.ModelSerializer):
    """Serializer for the Scoring model."""

    class Meta:
        model = Scoring
        fields = ("id", "tournament", "user", "score")


class RankSerializer(serializers.ModelSerializer):
    """Serializer for the Rank model."""

    class Meta:
        model = Rank
        fields = ("id", "name", "image", "required_score")


class GameManagerSerializer(serializers.ModelSerializer):
    """Serializer for the GameManager model."""

    class Meta:
        model = GameManager
        fields = ("id", "user", "game")

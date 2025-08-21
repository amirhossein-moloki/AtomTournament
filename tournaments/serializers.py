from rest_framework import serializers

from users.serializers import TeamSerializer, UserReadOnlySerializer

from .models import (Game, GameImage, GameManager, Match, Participant, Rank,
                     Report, Scoring, Tournament, WinnerSubmission)
from .validators import FileValidator


class GameImageSerializer(serializers.ModelSerializer):
    """Serializer for the GameImage model."""

    class Meta:
        model = GameImage
        fields = ("game", "image_type", "image")


class GameCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating games."""

    class Meta:
        model = Game
        fields = ("name", "description")


class GameReadOnlySerializer(serializers.ModelSerializer):
    """Serializer for the Game model (read-only)."""

    images = GameImageSerializer(many=True, read_only=True)

    class Meta:
        model = Game
        fields = ("id", "name", "description", "images")
        read_only_fields = fields


class TournamentCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating tournaments."""

    class Meta:
        model = Tournament
        fields = (
            "name",
            "image",
            "game",
            "start_date",
            "end_date",
            "is_free",
            "entry_fee",
            "rules",
            "type",
            "required_verification_level",
            "min_rank",
            "max_rank",
            "max_participants",
            "team_size",
            "mode",
        )


class TournamentReadOnlySerializer(serializers.ModelSerializer):
    """Serializer for reading tournament data."""

    participants = UserReadOnlySerializer(many=True, read_only=True)
    teams = TeamSerializer(many=True, read_only=True)
    game = GameReadOnlySerializer(read_only=True)
    creator = UserReadOnlySerializer(read_only=True)

    final_rank = serializers.SerializerMethodField()
    prize_won = serializers.SerializerMethodField()
    spots_left = serializers.SerializerMethodField()

    class Meta:
        model = Tournament
        fields = (
            "id",
            "name",
            "image",
            "game",
            "start_date",
            "end_date",
            "is_free",
            "entry_fee",
            "rules",
            "type",
            "participants",
            "teams",
            "creator",
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

    def get_spots_left(self, obj):
        if obj.max_participants is None:
            return None
        if obj.type == "individual":
            return obj.max_participants - obj.participants.count()
        else:
            return obj.max_participants - obj.teams.count()

    def get_final_rank(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None

        for p in obj.participant_set.all():
            if p.user_id == request.user.id:
                return p.rank
        return None

    def get_prize_won(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None

        for p in obj.participant_set.all():
            if p.user_id == request.user.id:
                return p.prize
        return None


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
        validators=[
            FileValidator(
                max_size=1024 * 1024 * 2, content_types=("image/jpeg", "image/png")
            )
        ],
    )

    class Meta:
        model = Match
        fields = ("result_proof",)


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
            "is_confirmed",
            "is_disputed",
            "dispute_reason",
            "room_id",
        )
        read_only_fields = fields


class ParticipantSerializer(serializers.ModelSerializer):
    """Serializer for the Participant model."""

    username = serializers.CharField(source="user.username", read_only=True)
    display_picture = serializers.SerializerMethodField()

    class Meta:
        model = Participant
        fields = [
            "user",
            "tournament",
            "username",
            "status",
            "rank",
            "prize",
            "display_picture",
        ]

    def get_display_picture(self, obj):
        if obj.tournament.type == "team":
            team = obj.user.teams.filter(tournaments=obj.tournament).first()
            if team and team.team_picture:
                return team.team_picture.url
        return obj.user.profile_picture.url if obj.user.profile_picture else None


class ReportSerializer(serializers.ModelSerializer):
    """Serializer for the Report model."""

    class Meta:
        model = Report
        fields = (
            "id",
            "reporter",
            "reported_user",
            "match",
            "description",
            "evidence",
            "status",
            "created_at",
        )
        read_only_fields = ("id", "reporter", "status", "created_at")


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


class ScoringSerializer(serializers.ModelSerializer):
    """Serializer for the Scoring model."""

    class Meta:
        model = Scoring
        fields = "__all__"


class RankSerializer(serializers.ModelSerializer):
    """Serializer for the Rank model."""

    class Meta:
        model = Rank
        fields = "__all__"


class GameManagerSerializer(serializers.ModelSerializer):
    """Serializer for the GameManager model."""

    class Meta:
        model = GameManager
        fields = "__all__"

from rest_framework import serializers
from users.serializers import TeamSerializer, UserSerializer

from .models import Game, Match, Tournament, Participant
from .validators import FileValidator


class GameSerializer(serializers.ModelSerializer):
    """Serializer for the Game model."""

    class Meta:
        model = Game
        fields = ("id", "name", "description")


class TournamentSerializer(serializers.ModelSerializer):
    """Serializer for the Tournament model."""

    participants = UserSerializer(many=True, read_only=True)
    teams = TeamSerializer(many=True, read_only=True)

    class Meta:
        model = Tournament
        fields = (
            "id",
            "name",
            "game",
            "start_date",
            "end_date",
            "is_free",
            "entry_fee",
            "rules",
            "type",
            "participants",
            "teams",
        )
        read_only_fields = ("id", "participants", "teams")


class MatchSerializer(serializers.ModelSerializer):
    """Serializer for the Match model."""

    participant1_user = UserSerializer(read_only=True)
    participant2_user = UserSerializer(read_only=True)
    participant1_team = TeamSerializer(read_only=True)
    participant2_team = TeamSerializer(read_only=True)
    winner_user = UserSerializer(read_only=True)
    winner_team = TeamSerializer(read_only=True)
    result_proof = serializers.ImageField(
        validators=[
            FileValidator(
                max_size=1024 * 1024 * 2, content_types=("image/jpeg", "image/png")
            )
        ]
    )

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
        )
        read_only_fields = (
            "id",
            "participant1_user",
            "participant2_user",
            "participant1_team",
            "participant2_team",
            "winner_user",
            "winner_team",
            "is_confirmed",
            "is_disputed",
        )


class ParticipantSerializer(serializers.ModelSerializer):
    """Serializer for the Participant model."""

    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Participant
        fields = ["username", "status"]

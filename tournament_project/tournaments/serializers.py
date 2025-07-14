from rest_framework import serializers
from users.serializers import TeamSerializer, UserSerializer

from .models import Game, Match, Tournament


class GameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = ("id", "name", "description")


class TournamentSerializer(serializers.ModelSerializer):
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

    def validate(self, data):
        """
        Check that start is before end.
        """
        if (
            "start_date" in data
            and "end_date" in data
            and data["start_date"] > data["end_date"]
        ):
            raise serializers.ValidationError("finish must occur after start")
        return data


from .validators import FileValidator


class MatchSerializer(serializers.ModelSerializer):
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

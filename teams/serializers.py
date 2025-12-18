from rest_framework import serializers

from users.serializers import UserReadOnlySerializer

from .models import Team, TeamInvitation


class TeamSerializer(serializers.ModelSerializer):
    """Serializer for the Team model."""

    members = UserReadOnlySerializer(many=True, read_only=True)

    class Meta:
        model = Team
        fields = ("id", "name", "captain", "members", "team_picture")
        read_only_fields = ("captain", "members")


class TeamInvitationSerializer(serializers.ModelSerializer):
    """Serializer for the TeamInvitation model."""

    team = TeamSerializer(read_only=True)

    class Meta:
        model = TeamInvitation
        fields = ("id", "from_user", "to_user", "team", "status", "timestamp")


class TopTeamSerializer(serializers.ModelSerializer):
    total_winnings = serializers.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        model = Team
        fields = ("id", "name", "total_winnings")

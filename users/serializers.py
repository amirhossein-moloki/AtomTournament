from rest_framework import serializers
from wallet.models import Wallet
from verification.serializers import VerificationSerializer

from .models import InGameID, Role, Team, User, TeamInvitation


class InGameIDSerializer(serializers.ModelSerializer):
    """Serializer for the InGameID model."""

    class Meta:
        model = InGameID
        fields = ("game", "player_id")


class UserSerializer(serializers.ModelSerializer):
    """Serializer for the User model."""

    in_game_ids = InGameIDSerializer(many=True, required=False)
    verification = VerificationSerializer(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "phone_number",
            "role",
            "in_game_ids",
            "password",
            "verification",
        )
        read_only_fields = ("id",)
        extra_kwargs = {"password": {"write_only": True}, "role": {"read_only": True}}

    def create(self, validated_data):
        in_game_ids_data = validated_data.pop("in_game_ids", [])
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        for in_game_id_data in in_game_ids_data:
            InGameID.objects.create(user=user, **in_game_id_data)
        return user

    def update(self, instance, validated_data):
        in_game_ids_data = validated_data.pop("in_game_ids", None)
        instance = super().update(instance, validated_data)

        if in_game_ids_data is not None:
            # Create a map of existing game IDs for quick lookups
            existing_ids = {
                item.game.id: item for item in instance.in_game_ids.all()
            }

            for item_data in in_game_ids_data:
                game = item_data["game"]
                if game.id in existing_ids:
                    # If item exists, update it and remove from the map
                    existing_item = existing_ids.pop(game.id)
                    existing_item.player_id = item_data["player_id"]
                    existing_item.save()
                else:
                    # If item doesn't exist, create it
                    InGameID.objects.create(user=instance, **item_data)

            # Any items left in the map were not in the new data, so delete them
            for item in existing_ids.values():
                item.delete()

        return instance


class TeamSerializer(serializers.ModelSerializer):
    """Serializer for the Team model."""

    class Meta:
        model = Team
        fields = ("id", "name", "captain", "members")
        read_only_fields = ("captain",)


class RoleSerializer(serializers.ModelSerializer):
    """Serializer for the Role model."""

    name = serializers.CharField(source="group.name")

    class Meta:
        model = Role
        fields = ("id", "name", "description")

    def update(self, instance, validated_data):
        members_data = validated_data.pop("members", [])
        instance = super().update(instance, validated_data)
        instance.members.set(members_data)
        return instance


class TeamInvitationSerializer(serializers.ModelSerializer):
    """Serializer for the TeamInvitation model."""

    class Meta:
        model = TeamInvitation
        fields = ("id", "from_user", "to_user", "team", "status", "timestamp")


class TopPlayerSerializer(serializers.ModelSerializer):
    total_winnings = serializers.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        model = User
        fields = ("id", "username", "total_winnings")


class TopTeamSerializer(serializers.ModelSerializer):
    total_winnings = serializers.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        model = Team
        fields = ("id", "name", "total_winnings")

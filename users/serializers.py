from rest_framework import serializers
from wallet.models import Wallet

from .models import InGameID, Role, Team, User


class InGameIDSerializer(serializers.ModelSerializer):
    """Serializer for the InGameID model."""

    class Meta:
        model = InGameID
        fields = ("game", "player_id")


class UserSerializer(serializers.ModelSerializer):
    """Serializer for the User model."""

    in_game_ids = InGameIDSerializer(many=True, required=False)

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
        )
        read_only_fields = ("id", "role")
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        in_game_ids_data = validated_data.pop("in_game_ids", [])
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        Wallet.objects.create(user=user)
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


class RoleSerializer(serializers.ModelSerializer):
    """Serializer for the Role model."""

    class Meta:
        model = Role
        fields = ("id", "name", "description")
        read_only_fields = ("id", "captain")

    def update(self, instance, validated_data):
        members_data = validated_data.pop("members", [])
        instance = super().update(instance, validated_data)
        instance.members.set(members_data)
        return instance

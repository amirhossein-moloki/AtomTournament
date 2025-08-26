from rest_framework import serializers

from verification.serializers import VerificationSerializer

from .models import InGameID, Role, Team, TeamInvitation, User, Referral


class InGameIDSerializer(serializers.ModelSerializer):
    """Serializer for the InGameID model."""

    class Meta:
        model = InGameID
        fields = ("game", "player_id")


class UserReadOnlySerializer(serializers.ModelSerializer):
    """Serializer for public User profiles (read-only)."""

    in_game_ids = InGameIDSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "profile_picture",
            "score",
            "rank",
            "role",
            "in_game_ids",
        )
        read_only_fields = fields


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new User."""

    email = serializers.EmailField(required=True)
    referral_code = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "phone_number",
            "password",
            "first_name",
            "last_name",
            "referral_code",
        )
        extra_kwargs = {
            "password": {"write_only": True},
        }

    def create(self, validated_data):
        referral_code = validated_data.pop('referral_code', None)
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()

        if referral_code:
            try:
                referrer = User.objects.get(referral_code=referral_code)
                Referral.objects.create(referrer=referrer, referred=user)
            except User.DoesNotExist:
                # If the referral code is invalid, we can either raise an error
                # or just ignore it. For a better user experience, we'll ignore it.
                pass

        return user


class UserSerializer(serializers.ModelSerializer):
    """Serializer for the User model (full view for owner)."""

    in_game_ids = InGameIDSerializer(many=True, required=False)
    verification = VerificationSerializer(read_only=True)
    role = serializers.ListField(child=serializers.CharField(), read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "profile_picture",
            "score",
            "rank",
            "role",
            "in_game_ids",
            "password",
            "verification",
        )
        read_only_fields = ("id", "score", "rank", "role", "verification")
        extra_kwargs = {
            "password": {"write_only": True, "required": False},
        }

    def update(self, instance, validated_data):
        # Handle password update separately
        password = validated_data.pop("password", None)
        if password:
            instance.set_password(password)

        in_game_ids_data = validated_data.pop("in_game_ids", None)
        instance = super().update(instance, validated_data)

        if in_game_ids_data is not None:
            # Create a map of existing game IDs for quick lookups
            existing_ids = {item.game.id: item for item in instance.in_game_ids.all()}

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
        fields = ("id", "name", "captain", "members", "team_picture")
        read_only_fields = ("captain",)


class RoleSerializer(serializers.ModelSerializer):
    """Serializer for the Role model."""

    name = serializers.CharField(source="group.name")

    class Meta:
        model = Role
        fields = ("id", "name", "description", "is_default")


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


class TopPlayerByRankSerializer(serializers.ModelSerializer):
    """Serializer for top players by rank."""

    rank = serializers.StringRelatedField()
    total_winnings = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    wins = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "score",
            "rank",
            "total_winnings",
            "wins",
            "profile_picture",
        )


class AdminLoginSerializer(serializers.Serializer):
    """Serializer for admin login."""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

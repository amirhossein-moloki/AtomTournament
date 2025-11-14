from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers

from verification.serializers import VerificationSerializer

from .models import InGameID, Role, User, Referral


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    pass


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
            "first_name",
            "last_name",
            "referral_code",
        )

    def create(self, validated_data):
        referral_code = validated_data.pop('referral_code', None)
        user = User(**validated_data)
        user.set_unusable_password()
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
            "verification",
        )
        read_only_fields = ("id", "score", "rank", "role", "verification")

    def update(self, instance, validated_data):
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


class RoleSerializer(serializers.ModelSerializer):
    """Serializer for the Role model."""

    name = serializers.CharField(source="group.name")

    class Meta:
        model = Role
        fields = ("id", "name", "description", "is_default")


class TopPlayerSerializer(serializers.ModelSerializer):
    total_winnings = serializers.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        model = User
        fields = ("id", "username", "total_winnings")


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



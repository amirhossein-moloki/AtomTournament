from rest_framework import serializers
from .models import User, Profile, InGameID, Team
from wallet.models import Wallet

class InGameIDSerializer(serializers.ModelSerializer):
    class Meta:
        model = InGameID
        fields = ('game', 'player_id')

class ProfileSerializer(serializers.ModelSerializer):
    in_game_ids = InGameIDSerializer(many=True, required=False)

    class Meta:
        model = Profile
        fields = ('in_game_ids',)

class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(required=False)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'phone_number', 'role', 'profile', 'password')
        read_only_fields = ('id', 'role')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        profile_data = validated_data.pop('profile', {})
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        Wallet.objects.create(user=user)
        in_game_ids_data = profile_data.get('in_game_ids', [])
        profile = Profile.objects.create(user=user)
        for in_game_id_data in in_game_ids_data:
            InGameID.objects.create(profile=profile, **in_game_id_data)
        return user

class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ('id', 'name', 'captain', 'members')
        read_only_fields = ('id', 'captain')

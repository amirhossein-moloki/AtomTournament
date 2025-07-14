from rest_framework import serializers
from .models import User, InGameID, Team
from wallet.models import Wallet

class InGameIDSerializer(serializers.ModelSerializer):
    class Meta:
        model = InGameID
        fields = ('game', 'player_id')

class UserSerializer(serializers.ModelSerializer):
    in_game_ids = InGameIDSerializer(many=True, required=False)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'phone_number', 'role', 'in_game_ids', 'password')
        read_only_fields = ('id', 'role')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        in_game_ids_data = validated_data.pop('in_game_ids', [])
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        Wallet.objects.create(user=user)
        for in_game_id_data in in_game_ids_data:
            InGameID.objects.create(user=user, **in_game_id_data)
        return user

class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ('id', 'name', 'captain', 'members')
        read_only_fields = ('id', 'captain')

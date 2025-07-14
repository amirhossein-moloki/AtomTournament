from rest_framework import serializers

from .models import (Game, Match, Profile, Team, Tournament, Transaction, User,
                     Wallet)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "phone_number", "role")


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ("id", "user", "in_game_ids")


class GameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = ("id", "name", "description")


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ("id", "name", "captain", "members")


class TournamentSerializer(serializers.ModelSerializer):
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
            "format",
            "participants",
            "teams",
        )


class MatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Match
        fields = (
            "id",
            "tournament",
            "round",
            "team1",
            "team2",
            "winner",
            "result_proof",
            "is_confirmed",
            "is_disputed",
        )


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ("id", "user", "total_balance", "withdrawable_balance")


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ("id", "wallet", "amount", "transaction_type", "timestamp")

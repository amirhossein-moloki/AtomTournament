from rest_framework import serializers
from .models import Game, Tournament, Match

class GameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = ('id', 'name', 'description')

class TournamentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tournament
        fields = ('id', 'name', 'game', 'start_date', 'end_date', 'is_free', 'entry_fee', 'rules', 'type', 'participants', 'teams')

class MatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Match
        fields = ('id', 'tournament', 'round', 'participants', 'teams', 'winner_user', 'winner_team', 'result_proof', 'is_confirmed', 'is_disputed')

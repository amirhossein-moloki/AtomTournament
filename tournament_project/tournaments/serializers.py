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
        read_only_fields = ('id',)

    def validate(self, data):
        """
        Check that start is before end.
        """
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError("finish must occur after start")
        return data

class MatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Match
        fields = ('id', 'tournament', 'round', 'participant1', 'participant2', 'winner', 'result_proof', 'is_confirmed', 'is_disputed')
        read_only_fields = ('id',)

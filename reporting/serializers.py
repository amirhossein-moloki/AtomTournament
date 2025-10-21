from rest_framework import serializers

class StatisticsSerializer(serializers.Serializer):
    total_prizes_paid = serializers.DecimalField(max_digits=15, decimal_places=2)
    active_users_count = serializers.IntegerField()
    total_tournaments_held = serializers.IntegerField()

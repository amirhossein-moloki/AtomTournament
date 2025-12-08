from rest_framework import serializers


class StatisticsSerializer(serializers.Serializer):
    total_prizes_paid = serializers.DecimalField(max_digits=15, decimal_places=2)
    active_users_count = serializers.IntegerField()
    total_tournaments_held = serializers.IntegerField()


class RevenueReportSerializer(serializers.Serializer):
    class SummarySerializer(serializers.Serializer):
        total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
        platform_share = serializers.DecimalField(max_digits=15, decimal_places=2)
        players_share = serializers.DecimalField(max_digits=15, decimal_places=2)
        start_date = serializers.DateTimeField()
        end_date = serializers.DateTimeField()

    class ByGameSerializer(serializers.Serializer):
        game_name = serializers.CharField()
        total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)

    class ByTournamentSerializer(serializers.Serializer):
        tournament_name = serializers.CharField()
        total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)

    class TimelineSerializer(serializers.Serializer):
        date = serializers.DateTimeField()
        revenue = serializers.DecimalField(max_digits=15, decimal_places=2)

    summary = SummarySerializer()
    by_game = ByGameSerializer(many=True)
    by_tournament = ByTournamentSerializer(many=True)
    timeline = TimelineSerializer(many=True)


class PlayersReportSerializer(serializers.Serializer):
    class SummarySerializer(serializers.Serializer):
        total_users = serializers.IntegerField()
        active_players = serializers.IntegerField()
        avg_participation_per_player = serializers.FloatField()
        start_date = serializers.DateTimeField()
        end_date = serializers.DateTimeField()

    class DistributionByGameSerializer(serializers.Serializer):
        game_name = serializers.CharField()
        player_count = serializers.IntegerField()
        percentage = serializers.FloatField()

    summary = SummarySerializer()
    distribution_by_game = DistributionByGameSerializer(many=True)


class TournamentReportSerializer(serializers.Serializer):
    class AllTournamentsSerializer(serializers.Serializer):
        name = serializers.CharField()
        game = serializers.CharField()
        start_date = serializers.DateTimeField()
        participant_count = serializers.IntegerField()
        capacity = serializers.IntegerField()
        fill_rate = serializers.FloatField()
        revenue = serializers.DecimalField(max_digits=15, decimal_places=2)

    class MostPopularSerializer(serializers.Serializer):
        name = serializers.CharField()
        participant_count = serializers.IntegerField()

    class MostProfitableSerializer(serializers.Serializer):
        name = serializers.CharField()
        revenue = serializers.DecimalField(max_digits=15, decimal_places=2)

    all_tournaments = AllTournamentsSerializer(many=True)
    most_popular = MostPopularSerializer(many=True)
    most_profitable = MostProfitableSerializer(many=True)


class FinancialReportSerializer(serializers.Serializer):
    class SummarySerializer(serializers.Serializer):
        total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
        total_prize_paid = serializers.DecimalField(max_digits=15, decimal_places=2)
        net_profit = serializers.DecimalField(max_digits=15, decimal_places=2)
        start_date = serializers.DateTimeField()
        end_date = serializers.DateTimeField()

    class CashFlowSerializer(serializers.Serializer):
        month = serializers.CharField()
        income = serializers.DecimalField(max_digits=15, decimal_places=2)
        expenses = serializers.DecimalField(max_digits=15, decimal_places=2)
        net_flow = serializers.DecimalField(max_digits=15, decimal_places=2)

    summary = SummarySerializer()
    cash_flow = CashFlowSerializer(many=True)


class MarketingReportSerializer(serializers.Serializer):
    class SummarySerializer(serializers.Serializer):
        total_referred_users = serializers.IntegerField()
        revenue_from_referred_users = serializers.DecimalField(
            max_digits=15, decimal_places=2
        )
        start_date = serializers.DateTimeField()
        end_date = serializers.DateTimeField()

    class ByReferrerSerializer(serializers.Serializer):
        referrer__username = serializers.CharField()
        new_users = serializers.IntegerField()

    summary = SummarySerializer()
    by_referrer = ByReferrerSerializer(many=True)

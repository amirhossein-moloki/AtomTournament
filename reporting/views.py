from django.db.models import Sum
from django.utils import timezone
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from tournaments.models import Tournament
from users.models import User
from wallet.models import Transaction
from .renderers import CSVRenderer
from .serializers import StatisticsSerializer
from .services import (
    generate_revenue_report,
    generate_players_report,
    generate_tournament_report,
    generate_financial_report,
    generate_marketing_report,
    ensure_bot_user,
)


class RevenueReportViewSet(ViewSet):
    """
    API endpoint for the Revenue Report.
    """
    permission_classes = [IsAdminUser]
    renderer_classes = [JSONRenderer, CSVRenderer]

    def list(self, request):
        # In a real app, you would parse filters from request.query_params
        report_data = generate_revenue_report()
        return Response(report_data)


class PlayersReportViewSet(ViewSet):
    """
    API endpoint for the Players Report.
    """
    permission_classes = [IsAdminUser]
    renderer_classes = [JSONRenderer, CSVRenderer]

    def list(self, request):
        report_data = generate_players_report()
        return Response(report_data)


class TournamentReportViewSet(ViewSet):
    """
    API endpoint for the Tournament Report.
    """
    permission_classes = [IsAdminUser]
    renderer_classes = [JSONRenderer, CSVRenderer]

    def list(self, request):
        report_data = generate_tournament_report()
        return Response(report_data)


class FinancialReportViewSet(ViewSet):
    """
    API endpoint for the Financial Report.
    """
    permission_classes = [IsAdminUser]
    renderer_classes = [JSONRenderer, CSVRenderer]

    def list(self, request):
        report_data = generate_financial_report()
        return Response(report_data)


class MarketingReportViewSet(ViewSet):
    """
    API endpoint for the Marketing Report.
    """
    permission_classes = [IsAdminUser]
    renderer_classes = [JSONRenderer, CSVRenderer]

    def list(self, request):
        report_data = generate_marketing_report()
        return Response(report_data)


def dashboard_callback(request, context):
    """
    This function is called by the Unfold admin theme to populate the
    dashboard with custom data.
    """
    context.update({
        "revenue_report": generate_revenue_report(),
        "players_report": generate_players_report(),
        "tournament_report": generate_tournament_report(),
        "financial_report": generate_financial_report(),
        "marketing_report": generate_marketing_report(),
    })

    return context


class StatisticsAPIView(APIView):
    """
    An endpoint to display overall platform statistics.
    """
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        ensure_bot_user()

        total_prizes_paid = (
            Transaction.objects.filter(
                transaction_type="prize", status="success"
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )
        active_users_count = User.objects.filter(is_active=True).count()
        total_tournaments_held = Tournament.objects.filter(
            end_date__lt=timezone.now()
        ).count()

        data = {
            "total_prizes_paid": total_prizes_paid,
            "active_users_count": active_users_count,
            "total_tournaments_held": total_tournaments_held,
        }

        serializer = StatisticsSerializer(data)
        return Response(serializer.data)

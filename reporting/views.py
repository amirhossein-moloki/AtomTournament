from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework.renderers import JSONRenderer
from .renderers import CSVRenderer
from .services import (
    generate_revenue_report,
    generate_players_report,
    generate_tournament_report,
    generate_financial_report,
    generate_marketing_report,
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

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RevenueReportViewSet,
    PlayersReportViewSet,
    TournamentReportViewSet,
    FinancialReportViewSet,
    MarketingReportViewSet,
)

router = DefaultRouter()
router.register(r'revenue', RevenueReportViewSet, basename='revenue-report')
router.register(r'players', PlayersReportViewSet, basename='players-report')
router.register(r'tournaments', TournamentReportViewSet, basename='tournament-report')
router.register(r'financial', FinancialReportViewSet, basename='financial-report')
router.register(r'marketing', MarketingReportViewSet, basename='marketing-report')

urlpatterns = [
    path('', include(router.urls)),
]

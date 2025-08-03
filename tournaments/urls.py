from django.urls import include, path

from .routers import router
from .views import (AdminReportListView, AdminWinnerSubmissionListView,
                    TopTournamentsView, TotalPrizeMoneyView,
                    TotalTournamentsView, UserTournamentHistoryView)

urlpatterns = [
    path("", include(router.urls)),
    path(
        "my-tournaments/",
        UserTournamentHistoryView.as_view(),
        name="my-tournament-history",
    ),
    path("admin/reports/", AdminReportListView.as_view(), name="admin-reports"),
    path(
        "admin/winner-submissions/",
        AdminWinnerSubmissionListView.as_view(),
        name="admin-winner-submissions",
    ),
    path("top-tournaments/", TopTournamentsView.as_view(), name="top-tournaments"),
    path(
        "total-prize-money/",
        TotalPrizeMoneyView.as_view(),
        name="total-prize-money",
    ),
    path(
        "total-tournaments/",
        TotalTournamentsView.as_view(),
        name="total-tournaments",
    ),
]

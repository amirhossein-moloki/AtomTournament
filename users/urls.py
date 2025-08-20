from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (AdminLoginView, DashboardView, RoleViewSet,
                    TeamMatchHistoryView, TeamViewSet, TopPlayersByRankView,
                    TopPlayersView, TopTeamsView, TotalPlayersView,
                    UserMatchHistoryView, UserViewSet)

router = DefaultRouter()
router.register(r"users", UserViewSet)
router.register(r"teams", TeamViewSet)
router.register(r"roles", RoleViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path(
        "users/<int:pk>/match-history/",
        UserMatchHistoryView.as_view(),
        name="user-match-history",
    ),
    path(
        "teams/<int:pk>/match-history/",
        TeamMatchHistoryView.as_view(),
        name="team-match-history",
    ),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("top-players/", TopPlayersView.as_view(), name="top-players"),
    path(
        "top-players-by-rank/",
        TopPlayersByRankView.as_view(),
        name="top-players-by-rank",
    ),
    path("top-teams/", TopTeamsView.as_view(), name="top-teams"),
    path("total-players/", TotalPlayersView.as_view(), name="total-players"),
    path("auth/admin-login/", AdminLoginView.as_view(), name="admin-login"),
]

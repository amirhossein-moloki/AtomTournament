from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (DashboardView, RoleViewSet, TeamViewSet, TopPlayersView,
                    TopTeamsView, TotalPlayersView, UserViewSet)

router = DefaultRouter()
router.register(r"users", UserViewSet)
router.register(r"teams", TeamViewSet)
router.register(r"roles", RoleViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("top-players/", TopPlayersView.as_view(), name="top-players"),
    path("top-teams/", TopTeamsView.as_view(), name="top-teams"),
    path("total-players/", TotalPlayersView.as_view(), name="total-players"),
]

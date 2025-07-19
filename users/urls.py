from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DashboardView,
    RoleViewSet,
    TeamViewSet,
    UserViewSet,
    TopPlayersView,
    TopTeamsView,
    TotalPlayersView,
)

router = DefaultRouter()
router.register(r"users", UserViewSet)
router.register(r"teams", TeamViewSet)
router.register(r"roles", RoleViewSet)

from .authentication_views import Level2AuthenticationRequestView, Level3AuthenticationRequestView

from .authentication_views import Level2AuthenticationRequestView, Level3AuthenticationRequestView, GetLevel3TextToReadView

urlpatterns = [
    path("", include(router.urls)),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("top-players/", TopPlayersView.as_view(), name="top-players"),
    path("top-teams/", TopTeamsView.as_view(), name="top-teams"),
    path("total-players/", TotalPlayersView.as_view(), name="total-players"),
    path("auth/level2/", Level2AuthenticationRequestView.as_view(), name="auth-level2"),
    path("auth/level3/", Level3AuthenticationRequestView.as_view(), name="auth-level3"),
    path("auth/level3/text/", GetLevel3TextToReadView.as_view(), name="auth-level3-text"),
]

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TeamMatchHistoryView, TeamViewSet, TopTeamsView

router = DefaultRouter()
router.register(r"teams", TeamViewSet, basename="team")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "teams/<int:pk>/match-history/",
        TeamMatchHistoryView.as_view(),
        name="team-match-history",
    ),
    path("top-teams/", TopTeamsView.as_view(), name="top-teams"),
]

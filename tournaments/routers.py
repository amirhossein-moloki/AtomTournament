from rest_framework.routers import DefaultRouter

from .views import (
    GameViewSet,
    MatchViewSet,
    ReportViewSet,
    TournamentViewSet,
    WinnerSubmissionViewSet,
)

router = DefaultRouter()
router.register(r"tournaments", TournamentViewSet)
router.register(r"matches", MatchViewSet)
router.register(r"games", GameViewSet)
router.register(r"reports", ReportViewSet)
router.register(r"winner-submissions", WinnerSubmissionViewSet)

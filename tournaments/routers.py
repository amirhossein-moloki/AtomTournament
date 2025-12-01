from rest_framework.routers import DefaultRouter

from .views import (GameViewSet, MatchViewSet, ReportViewSet,
                    TournamentColorViewSet, TournamentImageViewSet,
                    TournamentViewSet, WinnerSubmissionViewSet)

router = DefaultRouter()
router.register(r"tournaments", TournamentViewSet, basename="tournament")
router.register(r"matches", MatchViewSet)
router.register(r"games", GameViewSet, basename="game")
router.register(r"reports", ReportViewSet)
router.register(r"winner-submissions", WinnerSubmissionViewSet)
router.register(r"tournament-images", TournamentImageViewSet)
router.register(r"tournament-colors", TournamentColorViewSet)

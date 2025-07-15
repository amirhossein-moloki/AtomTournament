from rest_framework.routers import DefaultRouter

from .views import GameViewSet, MatchViewSet, TournamentViewSet

router = DefaultRouter()
router.register(r"tournaments", TournamentViewSet)
router.register(r"matches", MatchViewSet)
router.register(r"games", GameViewSet)

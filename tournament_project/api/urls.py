from django.urls import path, include
from rest_framework.routers import DefaultRouter
from users.views import UserViewSet, TeamViewSet
from tournaments.views import GameViewSet, TournamentViewSet, MatchViewSet
from wallet.views import WalletViewSet, TransactionViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'teams', TeamViewSet)
router.register(r'games', GameViewSet)
router.register(r'tournaments', TournamentViewSet)
router.register(r'matches', MatchViewSet)
router.register(r'wallets', WalletViewSet)
router.register(r'transactions', TransactionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

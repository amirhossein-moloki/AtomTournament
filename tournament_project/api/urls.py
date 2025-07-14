from django.urls import include, path
from rest_framework.routers import DefaultRouter
from tournaments.views import GameViewSet, MatchViewSet, TournamentViewSet
from users.views import TeamViewSet, UserViewSet
from wallet.views import TransactionViewSet, WalletViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r"users", UserViewSet)
router.register(r"teams", TeamViewSet)
router.register(r"games", GameViewSet)
router.register(r"tournaments", TournamentViewSet)
router.register(r"matches", MatchViewSet)
router.register(r"wallets", WalletViewSet)
router.register(r"transactions", TransactionViewSet)

urlpatterns = [
    path("", include(router.urls)),
]

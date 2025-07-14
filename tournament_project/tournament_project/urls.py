from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.conf import settings
from django.conf.urls.static import static
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
    path('admin/', admin.site.urls),
    path('api/v1/', include(router.urls)),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

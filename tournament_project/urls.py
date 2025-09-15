from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
# Import drf-spectacular views
from drf_spectacular.views import (SpectacularAPIView, SpectacularRedocView,
                                   SpectacularSwaggerView)

from tournaments.views import private_media_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("select2/", include("django_select2.urls")),
    # Add drf-spectacular URLs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    path("api/users/", include("users.urls")),
    path("api/tournaments/", include("tournaments.urls")),
    path("api/chat/", include("chat.urls")),
    path("api/wallet/", include("wallet.urls")),
    path("api/notifications/", include("notifications.urls")),
    re_path(r"^private-media/(?P<path>.*)$", private_media_view, name="private_media"),
    path("auth/", include("djoser.urls")),
    path("auth/", include("djoser.urls.jwt")),
    path("api/support/", include("support.urls")),
    path("api/verification/", include("verification.urls")),
    path("api/rewards/", include("rewards.urls")),
    path("api/reporting/", include("reporting.urls")),
    path("api/management/", include("management_dashboard.urls")),
    path("api/atomgamebot/", include("atomgamebot.urls")),
    path("api/", include("blog.urls")),
]

if settings.DEBUG:
    urlpatterns += [path("silk/", include("silk.urls", namespace="silk"))]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

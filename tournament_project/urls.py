from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from tournaments.views import private_media_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/users/", include("users.urls")),
    path("api/tournaments/", include("tournaments.urls")),
    path("api/chat/", include("chat.urls")),
    path("api/wallet/", include("wallet.urls")),
    path("api/notifications/", include("notifications.urls")),
    path("api/notifications/", include("notifications.urls")),
    re_path(r"^private-media/(?P<path>.*)$", private_media_view, name="private_media"),
    path("auth/", include("djoser.urls")),
    path("auth/", include("djoser.urls.jwt")),
    path("api/support/", include("support.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

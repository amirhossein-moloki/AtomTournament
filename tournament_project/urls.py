from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from tournaments.views import private_media_view

schema_view = get_schema_view(
    openapi.Info(
        title="Tournament Platform API",
        default_version="v1",
        description="API documentation for the Tournament Platform",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@tournament.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    re_path(
        r"^swagger(?P<format>\.json|\.yaml)$",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    re_path(
        r"^swagger/$",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    re_path(
        r"^redoc/$", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"
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
    path("api/verification/", include("verification.urls")),
    path("api/rewards/", include("rewards.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

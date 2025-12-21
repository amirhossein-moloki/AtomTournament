from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path

# Import drf-spectacular views
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from tournaments.views import private_media_view
from tournament_project.ckeditor_views import ckeditor5_upload
from blog.ckeditor_views import ckeditor_upload_view
from .views import page_not_found_view

handler404 = page_not_found_view

urlpatterns = [
    # --- JWT Token Authentication ---
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # --- Admin Panel ---
    path(
        "ckeditor5/image_upload/",
        ckeditor5_upload,
        name="ck_editor_5_upload_file",
    ),
    path("ckeditor5/", include("django_ckeditor_5.urls")),
    path("admin/", admin.site.urls),

    # --- Third-party integrations ---
    path("api/select2/", include("django_select2.urls")),

    # --- API Documentation (drf-spectacular) ---
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

    # --- App URLs ---
    path("api/users/", include("users.urls")),
    path("api/teams/", include("teams.urls")),
    path("api/tournaments/", include("tournaments.urls")),
    path("api/chat/", include("chat.urls")),
    path("api/wallet/", include("wallet.urls")),
    path("api/notifications/", include("notifications.urls")),
    re_path(
        r"^api/private-media/(?P<path>.*)$",
        private_media_view,
        name="private_media",
    ),
    path("api/support/", include("support.urls")),
    path("api/verification/", include("verification.urls")),
    path("api/rewards/", include("rewards.urls")),
    path("api/reporting/", include("reporting.urls")),
    path("api/management/", include("management_dashboard.urls")),
    path("api/atomgamebot/", include("atomgamebot.urls")),
    path("api/blog/", include("blog.urls", namespace="blog")),
    path("blog/upload/", ckeditor_upload_view, name="ckeditor_upload"),
]

# --- Debug Tools & Static/Media ---
if settings.DEBUG:
    urlpatterns += [path("api/silk/", include("silk.urls", namespace="silk"))]
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )

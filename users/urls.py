from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (CustomTokenObtainPairView, DashboardView, GoogleLoginView,
                    RoleViewSet, TopPlayersByRankView, TopPlayersView,
                    TotalPlayersView, UserMatchHistoryView, UserViewSet)

router = DefaultRouter()
router.register(r"users", UserViewSet)
router.register(r"roles", RoleViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path(
        "users/<int:pk>/match-history/",
        UserMatchHistoryView.as_view(),
        name="user-match-history",
    ),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("top-players/", TopPlayersView.as_view(), name="top-players"),
    path(
        "top-players-by-rank/",
        TopPlayersByRankView.as_view(),
        name="top-players-by-rank",
    ),
    path("total-players/", TotalPlayersView.as_view(), name="total-players"),
    path(
        "auth/admin-login/",
        CustomTokenObtainPairView.as_view(),
        name="admin-login",
    ),
    path(
        "auth/google/login/",
        GoogleLoginView.as_view(),
        name="google-login",
    ),
]

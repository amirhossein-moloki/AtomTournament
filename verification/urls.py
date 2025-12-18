from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import VerificationViewSet

router = DefaultRouter()
# The app is already mounted at /api/verification/, so we register the viewset at
# the root to avoid redundant path segments like /api/verification/verifications/.
router.register(r"", VerificationViewSet, basename="verification")

urlpatterns = [
    path("", include(router.urls)),
]

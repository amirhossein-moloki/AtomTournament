from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import SpinViewSet, WheelViewSet

router = DefaultRouter()
router.register(r"wheels", WheelViewSet)
router.register(r"spins", SpinViewSet, basename="spin")

urlpatterns = [
    path("", include(router.urls)),
]

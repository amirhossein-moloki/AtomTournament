from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WheelViewSet, SpinViewSet

router = DefaultRouter()
router.register(r"wheels", WheelViewSet)
router.register(r"spins", SpinViewSet, basename="spin")

urlpatterns = [
    path("", include(router.urls)),
]

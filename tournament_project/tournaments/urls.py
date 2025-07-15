from django.urls import include, path

from .routers import router

urlpatterns = [
    path("", include(router.urls)),
]

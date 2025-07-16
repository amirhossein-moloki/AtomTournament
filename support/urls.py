from django.urls import include, path
from rest_framework_nested import routers
from .views import TicketViewSet, TicketMessageViewSet

router = routers.DefaultRouter()
router.register(r"tickets", TicketViewSet)

tickets_router = routers.NestedSimpleRouter(router, r"tickets", lookup="ticket")
tickets_router.register(r"messages", TicketMessageViewSet, basename="ticket-messages")

urlpatterns = [
    path("", include(router.urls)),
    path("", include(tickets_router.urls)),
]

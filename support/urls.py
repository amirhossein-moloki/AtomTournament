from django.urls import include, path
from rest_framework_nested import routers

from .views import (SupportAssignmentViewSet, TicketMessageViewSet,
                    TicketViewSet)

router = routers.DefaultRouter()
router.register(r"tickets", TicketViewSet)
router.register(r"support-assignments", SupportAssignmentViewSet)

tickets_router = routers.NestedSimpleRouter(router, r"tickets", lookup="ticket")
tickets_router.register(r"messages", TicketMessageViewSet, basename="ticket-messages")

urlpatterns = [
    path("", include(router.urls)),
    path("", include(tickets_router.urls)),
]

from django.urls import include, path
from rest_framework_nested import routers

from .views import AttachmentViewSet, ConversationViewSet, MessageViewSet

router = routers.DefaultRouter()
router.register(r"conversations", ConversationViewSet, basename="conversation")

router.register(r"messages", MessageViewSet, basename="message")

messages_router = routers.NestedDefaultRouter(router, r"messages", lookup="message")
messages_router.register(r"attachments", AttachmentViewSet, basename="attachment")

urlpatterns = [
    path("", include(router.urls)),
    path("", include(messages_router.urls)),
]

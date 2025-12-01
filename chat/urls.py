from django.urls import include, path
from rest_framework_nested import routers

from .views import AttachmentViewSet, ConversationViewSet, MessageViewSet

router = routers.DefaultRouter()
router.register(r"conversations", ConversationViewSet, basename="conversation")
router.register(r"messages", MessageViewSet, basename="message")

conversations_router = routers.NestedDefaultRouter(
    router, r"conversations", lookup="conversation"
)
conversations_router.register(
    r"messages", MessageViewSet, basename="conversation-messages"
)

# Nested router for attachments under messages
messages_router = routers.NestedDefaultRouter(
    conversations_router, r"messages", lookup="message"
)
messages_router.register(
    r"attachments", AttachmentViewSet, basename="conversation-message-attachments"
)


urlpatterns = [
    path("", include(router.urls)),
    path("", include(conversations_router.urls)),
    path("", include(messages_router.urls)),
]

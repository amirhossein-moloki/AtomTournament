from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Attachment, Conversation, Message
from .permissions import IsSenderOrReadOnly
from .serializers import (
    AttachmentSerializer,
    ConversationSerializer,
    MessageSerializer,
)


class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.request.user.conversations.prefetch_related(
            "participants", "messages"
        )


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated, IsSenderOrReadOnly]

    def get_queryset(self):
        return Message.objects.filter(
            conversation__in=self.request.user.conversations.all()
        )

    def perform_create(self, serializer):
        conversation = get_object_or_404(
            Conversation, pk=self.kwargs["conversation_pk"]
        )
        serializer.save(sender=self.request.user, conversation=conversation)


class AttachmentViewSet(viewsets.ModelViewSet):
    queryset = Attachment.objects.all()
    serializer_class = AttachmentSerializer
    permission_classes = [IsAuthenticated]

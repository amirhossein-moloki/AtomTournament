from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import Attachment, Conversation, Message
from .permissions import IsSenderOrReadOnly, IsParticipantInConversation
from .serializers import (
    AttachmentSerializer,
    ConversationSerializer,
    MessageSerializer,
)


class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing conversations.
    """
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.request.user.conversations.prefetch_related(
            "participants", "messages"
        )


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing messages.
    """
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated, IsSenderOrReadOnly]

    def get_queryset(self):
        return Message.objects.filter(
            conversation__in=self.request.user.conversations.all()
        ).select_related('sender').prefetch_related('attachments')

    def perform_create(self, serializer):
        conversation = get_object_or_404(
            Conversation, pk=self.kwargs["conversation_pk"]
        )
        serializer.save(sender=self.request.user, conversation=conversation)


class AttachmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing attachments.
    """
    queryset = Attachment.objects.all()
    serializer_class = AttachmentSerializer
    permission_classes = [IsAuthenticated, IsParticipantInConversation]

    def get_queryset(self):
        return Attachment.objects.filter(message__pk=self.kwargs['message_pk'])

    def perform_create(self, serializer):
        message = get_object_or_404(Message, pk=self.kwargs['message_pk'])
        serializer.save(message=message)

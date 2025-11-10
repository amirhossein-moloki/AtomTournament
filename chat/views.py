from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from users.models import User

from .models import Attachment, Conversation, Message
from .permissions import IsParticipantInConversation, IsSenderOrReadOnly
from .serializers import (AttachmentCreateSerializer, AttachmentSerializer,
                          ConversationSerializer, MessageCreateSerializer,
                          MessageSerializer)


class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing conversations.
    """

    queryset = Conversation.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        return ConversationSerializer

    def get_queryset(self):
        return self.request.user.conversations.prefetch_related(
            "participants", "messages"
        )


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing messages.
    """

    queryset = Message.objects.all()
    permission_classes = [IsAuthenticated, IsSenderOrReadOnly]

    def get_serializer_class(self):
        if self.action == "create":
            return MessageCreateSerializer
        return MessageSerializer

    def get_queryset(self):
        return (
            Message.objects.filter(
                conversation__in=self.request.user.conversations.all()
            )
            .select_related("sender")
            .prefetch_related("attachments")
        )

    def perform_create(self, serializer):
        recipient_id = serializer.validated_data.pop("recipient_id")
        recipient = get_object_or_404(User, pk=recipient_id)

        conversation = (
            Conversation.objects.filter(participants=self.request.user)
            .filter(participants=recipient)
            .first()
        )

        if not conversation:
            conversation = Conversation.objects.create()
            conversation.participants.add(self.request.user, recipient)

        serializer.save(sender=self.request.user, conversation=conversation)


class AttachmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing attachments.
    """

    queryset = Attachment.objects.all()
    permission_classes = [IsAuthenticated, IsParticipantInConversation]

    def get_serializer_class(self):
        if self.action == "create":
            return AttachmentCreateSerializer
        return AttachmentSerializer

    def get_queryset(self):
        return Attachment.objects.filter(message__pk=self.kwargs["message_pk"])

    def perform_create(self, serializer):
        message = get_object_or_404(Message, pk=self.kwargs["message_pk"])
        serializer.save(message=message)

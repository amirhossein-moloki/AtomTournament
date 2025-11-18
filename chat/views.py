from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from users.models import User

from .models import Attachment, Conversation, Message
from .permissions import IsParticipantInConversation
from .serializers import (AttachmentCreateSerializer, AttachmentSerializer,
                          ConversationSerializer, MessageCreateSerializer,
                          MessageSerializer)


class ConversationViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet for managing conversations.
    Made read-only for creation, as conversations are created with the first message.
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
    - Creation is done via the top-level /api/messages/ endpoint.
    - Listing is done via the nested /api/conversations/<conversation_pk>/messages/ endpoint.
    """

    queryset = Message.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return MessageCreateSerializer
        return MessageSerializer

    def get_queryset(self):
        if "conversation_pk" in self.kwargs:
            conversation_pk = self.kwargs["conversation_pk"]
            # Ensure user is a participant of the conversation
            return (
                Message.objects.filter(
                    conversation__pk=conversation_pk,
                    conversation__participants=self.request.user,
                )
                .select_related("sender")
                .prefetch_related("attachments")
                .order_by("timestamp")
            )
        return Message.objects.none()

    def perform_create(self, serializer):
        recipient_id = serializer.validated_data.pop("recipient_id")
        recipient = get_object_or_404(User, id=recipient_id)

        # Find if a conversation already exists between the two users
        conversation = (
            Conversation.objects.filter(participants=self.request.user)
            .filter(participants=recipient)
            .first()
        )

        # If not, create a new conversation
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

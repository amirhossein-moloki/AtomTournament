from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import mixins, viewsets
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated

from users.models import User

from .models import Attachment, Conversation, Message
from .permissions import IsParticipantInConversation, IsSenderOrReadOnly
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
    permission_classes = [IsAuthenticated, IsSenderOrReadOnly]

    def get_serializer_class(self):
        if self.action == "create":
            return MessageCreateSerializer
        return MessageSerializer

    def get_queryset(self):
        if "conversation_pk" in self.kwargs:
            conversation_pk = self.kwargs["conversation_pk"]
            queryset = Message.objects.filter(conversation__pk=conversation_pk)

            # Ensure user is a participant of the conversation
            queryset = queryset.filter(conversation__participants=self.request.user)

            return queryset.select_related("sender").prefetch_related("attachments").order_by("timestamp")

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


@extend_schema(
    parameters=[
        OpenApiParameter(name='conversation_pk', type=int, location=OpenApiParameter.PATH, description='A unique integer value identifying this conversation.'),
    ]
)
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
        conversation_pk = self.kwargs.get("conversation_pk")
        if not conversation_pk:
            raise NotFound("Conversation not specified.")

        queryset = Attachment.objects.filter(
            message__pk=self.kwargs.get("message_pk"),
            message__conversation__pk=conversation_pk,
        )

        return queryset.filter(message__conversation__participants=self.request.user)

    def perform_create(self, serializer):
        conversation_pk = self.kwargs.get("conversation_pk")
        if not conversation_pk:
            raise NotFound("Conversation not specified.")

        message_queryset = Message.objects.filter(
            pk=self.kwargs["message_pk"], conversation__pk=conversation_pk
        )

        message_queryset = message_queryset.filter(
            conversation__participants=self.request.user
        )

        message = get_object_or_404(message_queryset)
        serializer.save(message=message)

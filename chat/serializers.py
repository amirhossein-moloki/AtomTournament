from rest_framework import serializers

from common.validators import validate_file
from users.models import User
from users.serializers import UserReadOnlySerializer

from .models import Attachment, Conversation, Message


class MessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new message."""

    recipient_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Message
        fields = ("content", "recipient_id")


class AttachmentSerializer(serializers.ModelSerializer):
    """Serializer for the Attachment model."""

    class Meta:
        model = Attachment
        fields = ("id", "message", "file", "uploaded_at")


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for the Message model."""

    sender = UserReadOnlySerializer(read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = (
            "id",
            "conversation",
            "sender",
            "content",
            "timestamp",
            "is_read",
            "is_edited",
            "is_deleted",
            "attachments",
        )


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer for the Conversation model."""

    participants = UserReadOnlySerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ("id", "participants", "created_at", "last_message", "support_ticket")

    def get_last_message(self, obj):
        """
        Get the last message of a conversation.
        """
        last_message = obj.messages.order_by("-timestamp").first()
        if last_message:
            return MessageSerializer(last_message).data
        return None


class AttachmentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new attachment."""

    class Meta:
        model = Attachment
        fields = ("file",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["file"].validators.append(validate_file)

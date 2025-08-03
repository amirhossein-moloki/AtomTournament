from rest_framework import serializers

from users.serializers import UserSerializer

from .models import Attachment, Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for the Message model."""

    sender = UserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ("id", "conversation", "sender", "content", "timestamp", "is_read", "is_edited", "is_deleted")


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer for the Conversation model."""

    participants = UserSerializer(many=True, read_only=True)
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


class AttachmentSerializer(serializers.ModelSerializer):
    """Serializer for the Attachment model."""

    class Meta:
        model = Attachment
        fields = ("id", "message", "file", "uploaded_at")

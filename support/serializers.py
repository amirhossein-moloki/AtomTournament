from rest_framework import serializers

from .models import SupportAssignment, Ticket, TicketAttachment, TicketMessage


class TicketAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketAttachment
        fields = ("id", "file", "created_at")


class TicketMessageSerializer(serializers.ModelSerializer):
    attachments = TicketAttachmentSerializer(many=True, read_only=True)
    files = serializers.ListField(
        child=serializers.FileField(), write_only=True, required=False
    )

    class Meta:
        model = TicketMessage
        fields = (
            "id",
            "ticket",
            "user",
            "message",
            "created_at",
            "attachments",
            "files",
        )
        read_only_fields = ("id", "user", "created_at", "ticket")

    def create(self, validated_data):
        validated_data.pop("files", None)
        return super().create(validated_data)


class TicketSerializer(serializers.ModelSerializer):
    messages = TicketMessageSerializer(many=True, read_only=True)

    class Meta:
        model = Ticket
        fields = ("id", "user", "title", "status", "created_at", "messages")
        read_only_fields = ("id", "user", "status", "created_at", "messages")


class SupportAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportAssignment
        fields = ("id", "support_person", "game", "head_support")

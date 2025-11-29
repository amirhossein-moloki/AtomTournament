from rest_framework import serializers
from common.validators import validate_file
from .models import SupportAssignment, Ticket, TicketAttachment, TicketMessage


class TicketAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketAttachment
        fields = ("id", "file", "created_at")


class TicketMessageSerializer(serializers.ModelSerializer):
    attachments = TicketAttachmentSerializer(many=True, read_only=True)
    uploaded_files = serializers.ListField(
        child=serializers.FileField(validators=[validate_file]), write_only=True, required=False
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
            "uploaded_files",
        )
        read_only_fields = ("id", "user", "created_at", "ticket")

class TicketSerializer(serializers.ModelSerializer):
    messages = TicketMessageSerializer(many=True, read_only=True)
    content = serializers.CharField(write_only=True)
    attachment = serializers.FileField(write_only=True, required=False, validators=[validate_file])

    class Meta:
        model = Ticket
        fields = (
            "id",
            "user",
            "title",
            "status",
            "created_at",
            "messages",
            "content",
            "attachment",
        )
        read_only_fields = ("id", "user", "status", "created_at", "messages")

    def create(self, validated_data):
        content = validated_data.pop("content")
        attachment_file = validated_data.pop("attachment", None)
        ticket = Ticket.objects.create(**validated_data)
        message = TicketMessage.objects.create(
            ticket=ticket, user=ticket.user, message=content
        )
        if attachment_file:
            TicketAttachment.objects.create(ticket_message=message, file=attachment_file)
        return ticket


class SupportAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportAssignment
        fields = ("id", "support_person", "game", "head_support")

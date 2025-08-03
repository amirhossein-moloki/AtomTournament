from rest_framework import serializers

from .models import SupportAssignment, Ticket, TicketMessage


class TicketMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketMessage
        fields = ("id", "ticket", "user", "message", "created_at")
        read_only_fields = ("id", "user", "created_at")


class TicketSerializer(serializers.ModelSerializer):
    messages = TicketMessageSerializer(many=True, read_only=True)

    class Meta:
        model = Ticket
        fields = ("id", "user", "title", "status", "created_at", "messages")
        read_only_fields = ("id", "user", "status", "created_at", "messages")


class SupportAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportAssignment
        fields = "__all__"

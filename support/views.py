from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated

from users.permissions import IsAdminUser, IsOwnerOrAdmin

from .models import SupportAssignment, Ticket, TicketAttachment, TicketMessage
from .serializers import (SupportAssignmentSerializer, TicketMessageSerializer,
                          TicketSerializer)


class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        queryset = (
            Ticket.objects.all().select_related("user").prefetch_related("messages")
        )
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TicketMessageViewSet(viewsets.ModelViewSet):
    queryset = TicketMessage.objects.all()
    serializer_class = TicketMessageSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        queryset = TicketMessage.objects.filter(ticket_id=self.kwargs["ticket_pk"])
        if not self.request.user.is_staff:
            queryset = queryset.filter(ticket__user=self.request.user)
        return queryset.select_related("user", "ticket")

    def perform_create(self, serializer):
        ticket = Ticket.objects.get(pk=self.kwargs["ticket_pk"])
        if not self.request.user.is_staff and ticket.user != self.request.user:
            raise PermissionDenied(
                "You do not have permission to add messages to this ticket."
            )

        uploaded_files = serializer.validated_data.pop("uploaded_files", [])
        message = serializer.save(user=self.request.user, ticket=ticket)
        for file_data in uploaded_files:
            TicketAttachment.objects.create(ticket_message=message, file=file_data)


class SupportAssignmentViewSet(viewsets.ModelViewSet):
    queryset = SupportAssignment.objects.all().select_related("support_person", "game")
    serializer_class = SupportAssignmentSerializer
    permission_classes = [IsAdminUser]

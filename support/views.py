from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from users.permissions import IsAdminUser

from .models import SupportAssignment, Ticket, TicketMessage
from .serializers import (SupportAssignmentSerializer, TicketMessageSerializer,
                          TicketSerializer)


class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]

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
        serializer.save(user=self.request.user, ticket=ticket)


class SupportAssignmentViewSet(viewsets.ModelViewSet):
    queryset = SupportAssignment.objects.all().select_related("support_person", "game")
    serializer_class = SupportAssignmentSerializer
    permission_classes = [IsAdminUser]

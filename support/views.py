from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Ticket, TicketMessage, SupportAssignment
from .serializers import (
    TicketSerializer,
    TicketMessageSerializer,
    SupportAssignmentSerializer,
)
from users.permissions import IsAdminUser


class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Ticket.objects.all()
        return Ticket.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TicketMessageViewSet(viewsets.ModelViewSet):
    queryset = TicketMessage.objects.all()
    serializer_class = TicketMessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TicketMessage.objects.filter(
            ticket__user=self.request.user, ticket_id=self.kwargs["ticket_pk"]
        )

    def perform_create(self, serializer):
        ticket = Ticket.objects.get(pk=self.kwargs["ticket_pk"], user=self.request.user)
        serializer.save(user=self.request.user, ticket=ticket)


class SupportAssignmentViewSet(viewsets.ModelViewSet):
    queryset = SupportAssignment.objects.all()
    serializer_class = SupportAssignmentSerializer
    permission_classes = [IsAdminUser]

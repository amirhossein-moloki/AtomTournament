from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Ticket, TicketMessage

User = get_user_model()


class SupportTicketModelTests(TestCase):
    def test_ticket_creation(self):
        user = User.objects.create_user(
            username="testuser", password="password", phone_number="+123"
        )
        ticket = Ticket.objects.create(user=user, title="Test Ticket")
        message = TicketMessage.objects.create(
            ticket=ticket,
            user=user,
            message="This is a test message.",
        )
        self.assertEqual(ticket.title, "Test Ticket")
        self.assertEqual(ticket.messages.count(), 1)
        self.assertEqual(message.message, "This is a test message.")

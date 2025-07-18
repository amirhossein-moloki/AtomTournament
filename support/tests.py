from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from users.models import User

from .models import Ticket


class SupportTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="user1", password="testpassword", phone_number="+12125552368"
        )
        self.client.force_authenticate(user=self.user)

    def test_create_ticket(self):
        url = reverse("ticket-list")
        data = {"title": "Test Ticket"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Ticket.objects.count(), 1)

    def test_create_ticket_message(self):
        ticket = Ticket.objects.create(user=self.user, title="Test Ticket")
        url = reverse("ticket-messages-list", kwargs={"ticket_pk": ticket.pk})
        data = {"message": "Test Message"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ticket.messages.count(), 1)

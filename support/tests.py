from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Ticket, TicketMessage

User = get_user_model()


class SupportTicketAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="password", phone_number="+123"
        )
        self.ticket = Ticket.objects.create(user=self.user, title="Test Ticket")
        self.client.force_authenticate(user=self.user)

    def test_create_ticket_message_with_attachment(self):
        url = reverse("ticket-messages-list", kwargs={"ticket_pk": self.ticket.pk})
        file = SimpleUploadedFile(
            "test_file.jpg", b"file_content", content_type="image/jpeg"
        )
        data = {"message": "This is a test message with an attachment.", "uploaded_files": [file]}
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TicketMessage.objects.count(), 1)
        self.assertEqual(
            TicketMessage.objects.first().attachments.count(), 1, response.json()
        )
        attachment = TicketMessage.objects.first().attachments.first()
        self.assertTrue(
            attachment.file.name.startswith("support_attachments/test_file")
        )
        self.assertTrue(attachment.file.name.endswith(".jpg"))

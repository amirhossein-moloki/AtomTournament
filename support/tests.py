from io import BytesIO
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from .models import Ticket, TicketMessage, TicketAttachment
from PIL import Image

User = get_user_model()


class TicketAPITest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('user', 'user@example.com', 'password')
        self.staff_user = User.objects.create_user('staff', 'staff@example.com', 'password', is_staff=True)
        self.client = APIClient()

    def _create_image(self, filename="test.jpg", size=(100, 100), image_format="JPEG"):
        """Helper to create a dummy image file."""
        buffer = BytesIO()
        Image.new("RGB", size).save(buffer, image_format)
        buffer.seek(0)
        return SimpleUploadedFile(
            filename, buffer.read(), content_type=f"image/{image_format.lower()}"
        )

    def test_create_ticket_with_avif_attachment(self):
        self.client.force_authenticate(user=self.user)
        image_file = self._create_image()
        data = {
            'title': 'Test Ticket with AVIF',
            'department': 'technical',
            'content': 'This is a test ticket with an attachment.',
            'attachment': image_file
        }
        response = self.client.post('/api/support/tickets/', data, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Ticket.objects.count(), 1)
        self.assertEqual(TicketMessage.objects.count(), 1)
        self.assertEqual(TicketAttachment.objects.count(), 1)

        ticket = Ticket.objects.first()
        self.assertEqual(ticket.title, 'Test Ticket with AVIF')

        attachment = TicketAttachment.objects.first()
        self.assertIsNotNone(attachment.file)
        # The file should be converted to .avif
        self.assertTrue(attachment.file.name.endswith(".avif"))

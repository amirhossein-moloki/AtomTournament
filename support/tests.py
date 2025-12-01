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
        self.user = User.objects.create_user(
            "user", "user@example.com", "password", phone_number="+15555555555"
        )
        self.staff_user = User.objects.create_user(
            "staff",
            "staff@example.com",
            "password",
            is_staff=True,
            phone_number="+15555555556",
        )
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
            "title": "Test Ticket with AVIF",
            "content": "This is a test ticket with an attachment.",
            "attachment": image_file,
        }
        response = self.client.post("/api/support/tickets/", data, format="multipart")

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

    def test_create_ticket_message_with_webp_attachment(self):
        self.client.force_authenticate(user=self.user)
        ticket = Ticket.objects.create(user=self.user, title="Test Ticket")
        image_file = self._create_image(filename="test.webp", image_format="WEBP")
        data = {
            "message": "Here is a webp file.",
            "uploaded_files": [image_file],
        }
        response = self.client.post(
            f"/api/support/tickets/{ticket.id}/messages/", data, format="multipart"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TicketMessage.objects.count(), 1)
        self.assertEqual(TicketAttachment.objects.count(), 1)

        attachment = TicketAttachment.objects.first()
        self.assertIsNotNone(attachment.file)
        # The OptimizedFileField converts images, so we check for the output format
        self.assertTrue(attachment.file.name.endswith(".avif"))

    def test_create_ticket_message_with_attachment_only(self):
        self.client.force_authenticate(user=self.user)
        ticket = Ticket.objects.create(user=self.user, title="Attachment Only Test")
        image_file = self._create_image()
        data = {
            "uploaded_files": [image_file],
        }
        response = self.client.post(
            f"/api/support/tickets/{ticket.id}/messages/", data, format="multipart"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TicketMessage.objects.count(), 1)
        self.assertEqual(TicketAttachment.objects.count(), 1)
        message = TicketMessage.objects.first()
        self.assertIsNone(message.message)

    def test_create_ticket_message_with_no_data(self):
        self.client.force_authenticate(user=self.user)
        ticket = Ticket.objects.create(user=self.user, title="No Data Test")
        data = {}
        response = self.client.post(
            f"/api/support/tickets/{ticket.id}/messages/", data, format="multipart"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["non_field_errors"][0],
            "شما باید یا یک پیام بنویسید یا حداقل یک فایل ارسال کنید.",
        )

    def test_create_ticket_message_with_invalid_file_type(self):
        self.client.force_authenticate(user=self.user)
        ticket = Ticket.objects.create(user=self.user, title="Invalid File Test")
        invalid_file = SimpleUploadedFile("test.txt", b"file_content", content_type="text/plain")
        data = {
            "uploaded_files": [invalid_file],
        }
        response = self.client.post(
            f"/api/support/tickets/{ticket.id}/messages/", data, format="multipart"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("uploaded_files", response.data)
        self.assertIn("فرمت فایل ‘.txt’ پشتیبانی نمی‌شود.", response.data["uploaded_files"][0][0])

    def test_create_ticket_message_with_oversized_file(self):
        self.client.force_authenticate(user=self.user)
        ticket = Ticket.objects.create(user=self.user, title="Oversized File Test")
        # Create a file larger than 10MB
        oversized_content = b"a" * (11 * 1024 * 1024)
        oversized_file = SimpleUploadedFile(
            "large_file.jpg", oversized_content, content_type="image/jpeg"
        )
        data = {
            "uploaded_files": [oversized_file],
        }
        response = self.client.post(
            f"/api/support/tickets/{ticket.id}/messages/", data, format="multipart"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("uploaded_files", response.data)
        self.assertIn(
            "حجم فایل شما بیشتر از ۱۰ مگابایت است.",
            response.data["uploaded_files"][0][0],
        )

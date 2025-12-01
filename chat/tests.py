from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from PIL import Image

from .models import Conversation, Message, Attachment

User = get_user_model()


class ChatAPITests(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user1", password="p", phone_number="+1"
        )
        self.user2 = User.objects.create_user(
            username="user2", password="p", phone_number="+2"
        )
        self.client.force_authenticate(user=self.user1)

    def test_create_message_and_conversation(self):
        url = reverse("message-list")
        data = {"content": "Hello, world!", "recipient_id": self.user2.id}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(Message.objects.count(), 1)
        conversation = Conversation.objects.first()
        self.assertIn(self.user1, conversation.participants.all())
        self.assertIn(self.user2, conversation.participants.all())
        self.assertEqual(Message.objects.first().conversation, conversation)


class AttachmentAPITests(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user1", password="p", phone_number="+1"
        )
        self.user2 = User.objects.create_user(
            username="user2", password="p", phone_number="+2"
        )
        self.client.force_authenticate(user=self.user1)
        # Create a conversation and a message to attach files to
        self.conversation = Conversation.objects.create()
        self.conversation.participants.add(self.user1, self.user2)
        self.message = Message.objects.create(
            conversation=self.conversation, sender=self.user1, content="Initial message"
        )
        self.url = reverse(
            "conversation-message-attachments-list",
            kwargs={
                "conversation_pk": self.conversation.pk,
                "message_pk": self.message.pk,
            },
        )

    def _create_image(self, filename="test.jpg", size=(100, 100), image_format="JPEG"):
        """Helper to create a dummy image file."""
        buffer = BytesIO()
        Image.new("RGB", size).save(buffer, image_format)
        buffer.seek(0)
        return SimpleUploadedFile(
            filename, buffer.read(), content_type=f"image/{image_format.lower()}"
        )

    @patch("chat.signals.convert_image_to_avif_task.delay")
    def test_create_attachment_successfully(self, mock_convert_task):
        image_file = self._create_image()
        data = {"file": image_file}
        response = self.client.post(self.url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Attachment.objects.count(), 1)
        attachment = Attachment.objects.first()
        self.assertEqual(attachment.message, self.message)
        self.assertTrue(attachment.file.name.endswith(".jpg"))
        # Verify that the optimization task was called
        mock_convert_task.assert_called_once()

    @patch("chat.signals.convert_image_to_avif_task.delay")
    def test_create_attachment_with_non_image_file(self, mock_convert_task):
        video_file = SimpleUploadedFile(
            "test.mp4", b"file_content", content_type="video/mp4"
        )
        data = {"file": video_file}
        response = self.client.post(self.url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Attachment.objects.count(), 1)
        # Verify that the optimization task was NOT called
        mock_convert_task.assert_not_called()

    def test_create_attachment_with_invalid_file_type(self):
        invalid_file = SimpleUploadedFile(
            "test.txt", b"file_content", content_type="text/plain"
        )
        data = {"file": invalid_file}
        response = self.client.post(self.url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file", response.data)
        self.assertTrue(
            any(
                "فرمت فایل ‘.txt’ پشتیبانی نمی‌شود." in str(e)
                for e in response.data["file"]
            )
        )

    def test_create_attachment_with_oversized_file(self):
        oversized_content = b"a" * (11 * 1024 * 1024)
        oversized_file = SimpleUploadedFile(
            "large_file.jpg", oversized_content, content_type="image/jpeg"
        )
        data = {"file": oversized_file}
        response = self.client.post(self.url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file", response.data)
        self.assertTrue(
            any("حجم فایل شما بیشتر از ۱۰ مگابایت است." in str(e) for e in response.data["file"])
        )

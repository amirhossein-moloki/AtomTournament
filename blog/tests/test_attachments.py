# blog/tests/test_attachments.py

from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.contrib.auth import get_user_model
from PIL import Image
from blog.models import Media, CustomAttachment
from blog.services import process_attachment

User = get_user_model()


class AttachmentServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")

    def _create_image(self, filename="test.jpg", size=(100, 100), image_format="JPEG"):
        """Helper to create a dummy image file."""
        buffer = BytesIO()
        Image.new("RGB", size).save(buffer, image_format)
        buffer.seek(0)
        return SimpleUploadedFile(
            filename, buffer.read(), content_type=f"image/{image_format.lower()}"
        )

    def test_image_attachment_is_converted_to_avif(self):
        """
        تست می‌کند که فایل‌های تصویری به درستی به فرمت AVIF تبدیل می‌شوند.
        """
        image = self._create_image()
        attachment = CustomAttachment(file=image, name="Test Image")

        # Mock request object if needed by the service
        request = type("Request", (), {"user": self.user})()

        processed_attachment = process_attachment(attachment, request=request)

        # بررسی می‌کنیم که یک آبجکت Media ساخته شده
        media = Media.objects.first()
        self.assertIsNotNone(media)
        self.assertEqual(media.title, "Test Image")
        self.assertEqual(media.uploaded_by, self.user)
        self.assertEqual(media.mime, "image/avif")
        self.assertTrue(media.storage_key.endswith(".avif"))

        # بررسی می‌کنیم که URL در Attachment ذخیره شده
        self.assertIsNotNone(processed_attachment.url)
        self.assertTrue(processed_attachment.file.name.endswith('.avif'))

    def test_non_image_attachment_is_not_converted(self):
        """
        تست می‌کند فایل‌های غیرتصویری تبدیل نمی‌شوند.
        """
        text_file = SimpleUploadedFile("test.txt", b"file_content", content_type="text/plain")
        attachment = CustomAttachment(file=text_file, name="Test Document")

        process_attachment(attachment)

        media = Media.objects.first()
        self.assertIsNotNone(media)
        self.assertEqual(media.mime, "text/plain")
        self.assertTrue(media.storage_key.endswith(".txt"))
        self.assertFalse(media.storage_key.endswith(".avif"))

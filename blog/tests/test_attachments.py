import shutil
import tempfile
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from PIL import Image

from blog.attachments import CustomAttachment
from blog.models import Media


def _make_test_image(name="test.png"):
    buffer = BytesIO()
    Image.new("RGB", (2, 2), (255, 0, 0)).save(buffer, format="PNG")
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class CustomAttachmentSaveTests(TestCase):
    def setUp(self):
        self.temp_media_root = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.temp_media_root)
        self.override.enable()
        self.factory = RequestFactory()

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.temp_media_root, ignore_errors=True)

    def test_save_without_request_creates_media_record(self):
        attachment = CustomAttachment(file=_make_test_image(), name="No Request")

        attachment.save()

        media = Media.objects.get(title="No Request")
        self.assertIsNone(media.uploaded_by)
        self.assertEqual(media.type, "image")
        self.assertEqual(media.mime, "image/webp")
        self.assertTrue(media.storage_key.endswith(".webp"))
        self.assertEqual(attachment.url, media.url)

    def test_save_with_request_uses_authenticated_user(self):
        user = get_user_model().objects.create_user("uploader", "uploader@example.com", "pass")
        request = self.factory.post("/upload")
        request.user = user

        attachment = CustomAttachment(file=_make_test_image("with_user.png"), name="With User")

        attachment.save(request=request)

        media = Media.objects.get(title="With User")
        self.assertEqual(media.uploaded_by, user)
        self.assertEqual(media.mime, "image/webp")
        self.assertEqual(attachment.url, media.url)

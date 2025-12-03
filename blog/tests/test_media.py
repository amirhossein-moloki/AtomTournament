import os
import shutil
from io import BytesIO
from PIL import Image

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage

from blog.models import Media

User = get_user_model()

TEST_MEDIA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_media')

@override_settings(MEDIA_ROOT=TEST_MEDIA_DIR)
class MediaAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_authenticate(user=self.user)

        if os.path.exists(TEST_MEDIA_DIR):
            shutil.rmtree(TEST_MEDIA_DIR)
        os.makedirs(TEST_MEDIA_DIR)

    def tearDown(self):
        if os.path.exists(TEST_MEDIA_DIR):
            shutil.rmtree(TEST_MEDIA_DIR)

    def _create_dummy_image(self, name="test.jpg", content_type="image/jpeg"):
        image_io = BytesIO()
        image = Image.new('RGB', (100, 100), color='red')
        image.save(image_io, 'jpeg')
        image_io.seek(0)
        return SimpleUploadedFile(name, image_io.getvalue(), content_type=content_type)

    def test_media_upload_and_optimization(self):
        """
        Tests that an uploaded image is correctly converted to AVIF format
        and that the response contains the full media details.
        """
        image_file = self._create_dummy_image(name="test_upload.jpg")

        # Upload the image via API
        response = self.client.post(reverse('media-list'), {'file': image_file}, format='multipart')

        # Assert successful creation and response structure
        self.assertEqual(response.status_code, 201, f"API returned errors: {response.content.decode()}")
        self.assertIn('id', response.data)
        self.assertIn('url', response.data)
        self.assertTrue(response.data['url'].endswith('.avif'))

        # Assert database state
        self.assertEqual(Media.objects.count(), 1)
        media = Media.objects.first()
        self.assertTrue(media.storage_key.endswith('.avif'))
        self.assertEqual(media.mime, 'image/avif')
        self.assertEqual(media.type, 'image')
        self.assertIsNotNone(media.width)
        self.assertIsNotNone(media.height)

        # Assert file existence
        self.assertTrue(default_storage.exists(media.storage_key))

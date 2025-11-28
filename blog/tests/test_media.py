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
from django.db.models.signals import post_save

from blog.models import Media
from blog.signals import queue_media_image_processing
from blog.tasks import convert_media_image_to_avif_task

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

    def test_media_avif_conversion_integration(self):
        """
        Tests the media conversion logic by manually calling the task,
        bypassing the problematic Celery-eager behavior in the test environment.
        """
        # 1. Disconnect the signal to prevent .delay() from being called
        post_save.disconnect(queue_media_image_processing, sender=Media)

        try:
            image_file = self._create_dummy_image(name="convert_me.jpg")

            # 2. Upload the image via API. This creates the Media object.
            response = self.client.post(reverse('media-list'), {'file': image_file}, format='multipart')
            self.assertEqual(response.status_code, 201, f"API returned errors: {response.content.decode()}")
            self.assertEqual(Media.objects.count(), 1)

            media = Media.objects.first()
            # At this point, the file should be the original JPG
            self.assertTrue(media.storage_key.endswith('.jpg'))

            # 3. Manually call the task function with the new media ID
            convert_media_image_to_avif_task(media.id)

            # 4. Assert that the file was converted
            media.refresh_from_db()
            self.assertTrue(media.storage_key.endswith('.avif'), f"Storage key {media.storage_key} does not end with .avif")
            self.assertEqual(media.mime, 'image/avif')
            self.assertTrue(media.size_bytes > 0)

            # 5. Assert that the new file exists and the old one is gone
            self.assertTrue(default_storage.exists(media.storage_key))
            storage_files = os.listdir(TEST_MEDIA_DIR)
            self.assertFalse(any(f.endswith('.jpg') for f in storage_files))
            self.assertTrue(any(f.endswith('.avif') for f in storage_files))

        finally:
            # 6. Reconnect the signal to ensure test isolation
            post_save.connect(queue_media_image_processing, sender=Media)

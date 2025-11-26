import os
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from blog.models import Media

User = get_user_model()

@override_settings(MEDIA_ROOT=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_media'))
class MediaAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_authenticate(user=self.user)
        self.image = SimpleUploadedFile("test.jpg", b"file_content", content_type="image/jpeg")

    def tearDown(self):
        # Clean up created media files
        for media in Media.objects.all():
            if os.path.exists(media.storage_key):
                os.remove(media.storage_key)

    @patch('blog.tasks.process_media_image.delay')
    def test_media_upload(self, mock_process_media_image):
        response = self.client.post(reverse('media-list'), {'file': self.image}, format='multipart')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Media.objects.count(), 1)
        media = Media.objects.first()
        self.assertEqual(media.title, 'test.jpg')
        mock_process_media_image.assert_called_once_with(media.id)

    def test_media_download(self):
        media = Media.objects.create(
            storage_key='test.jpg',
            title='test.jpg',
            type='image',
            mime='image/jpeg',
            size_bytes=12,
            uploaded_by=self.user
        )
        with open(media.storage_key, 'wb') as f:
            f.write(b'file_content')

        response = self.client.get(reverse('download_media', kwargs={'media_id': media.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Disposition'], 'attachment; filename="test.jpg"')
        self.assertEqual(b"".join(response.streaming_content), b'file_content')

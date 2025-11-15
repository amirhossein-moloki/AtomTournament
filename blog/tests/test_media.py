from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status

from blog.factories import MediaFactory
from blog.models import Media
from blog.tests.base import BaseAPITestCase


class MediaAPITest(BaseAPITestCase):
    @patch('blog.views.process_media_image.delay')
    def test_upload_image(self, mock_task):
        """
        Ensures we can upload an image and the celery task is called.
        """
        self._authenticate_as_staff()
        url = reverse('media-list')
        image = SimpleUploadedFile("test.jpg", b"file_content", content_type="image/jpeg")
        data = {
            'storage_key': 'test_key',
            'url': 'http://example.com/test.jpg',
            'type': 'image',
            'mime': 'image/jpeg',
            'size_bytes': 12345,
            'alt_text': 'a test image',
            'title': 'Test Image',
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Media.objects.filter(storage_key='test_key').exists())
        media_instance = Media.objects.get(storage_key='test_key')
        mock_task.assert_called_once_with(media_instance.id)

    def test_list_media(self):
        """
        Ensures we can list media files.
        """
        MediaFactory.create_batch(4)
        url = reverse('media-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)

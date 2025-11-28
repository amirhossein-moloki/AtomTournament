from django.db.models.signals import post_save
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from blog.factories import UserFactory
from blog.models import AuthorProfile, Media
from blog.signals import queue_media_image_processing


class BaseAPITestCase(APITestCase):
    def setUp(self):
        super().setUp()

        # Disconnect the signal to prevent automatic AVIF conversion in unrelated tests
        post_save.disconnect(queue_media_image_processing, sender=Media)

        self.user = UserFactory()
        self.author_profile = AuthorProfile.objects.get(user=self.user)
        self.staff_user = UserFactory(is_staff=True)
        self.staff_author_profile = AuthorProfile.objects.get(user=self.staff_user)

    def tearDown(self):
        # Reconnect the signal to ensure it's available for other tests
        post_save.connect(queue_media_image_processing, sender=Media)
        super().tearDown()

    def _get_jwt_token(self, user):
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    def _authenticate(self, user=None):
        user_to_auth = user or self.user
        token = self._get_jwt_token(user_to_auth)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def _authenticate_as_staff(self):
        self._authenticate(self.staff_user)

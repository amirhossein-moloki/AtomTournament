from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from blog.factories import UserFactory, AuthorProfileFactory


class BaseAPITestCase(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = UserFactory()
        self.author_profile = AuthorProfileFactory(user=self.user)
        self.staff_user = UserFactory(is_staff=True)
        self.staff_author_profile = AuthorProfileFactory(user=self.staff_user)

    def _get_jwt_token(self, user):
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    def _authenticate(self, user=None):
        user_to_auth = user or self.user
        token = self._get_jwt_token(user_to_auth)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def _authenticate_as_staff(self):
        self._authenticate(self.staff_user)

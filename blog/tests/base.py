from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from blog.factories import UserFactory
from blog.models import AuthorProfile


class BaseAPITestCase(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = UserFactory()
        self.author_profile, _ = AuthorProfile.objects.get_or_create(
            user=self.user, defaults={'display_name': self.user.username}
        )
        self.staff_user = UserFactory(is_staff=True)
        self.staff_author_profile, _ = AuthorProfile.objects.get_or_create(
            user=self.staff_user, defaults={'display_name': self.staff_user.username}
        )

    def tearDown(self):
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

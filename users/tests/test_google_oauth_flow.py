from unittest.mock import patch, MagicMock

from django.urls import reverse
from django.conf import settings
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import User


@override_settings(
    GOOGLE_CLIENT_ID="test_client_id",
    GOOGLE_REDIRECT_URI="http://test.com/callback",
    FRONTEND_URL="http://test-frontend.com",
)
class GoogleOAuthFlowTest(APITestCase):
    def setUp(self):
        self.redirect_url = reverse("google-login-redirect")
        self.callback_url = reverse("google-login-callback")

    def test_google_login_redirect(self):
        """
        Test that the redirect view correctly redirects to Google's authentication page.
        """
        response = self.client.get(self.redirect_url)
        from urllib.parse import urlencode

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("accounts.google.com", response.url)
        self.assertIn(settings.GOOGLE_CLIENT_ID, response.url)
        self.assertIn(urlencode({"redirect_uri": settings.GOOGLE_REDIRECT_URI}), response.url)

    @patch("users.views.requests.post")
    @patch("users.services.google_id_token.verify_oauth2_token")
    def test_google_login_callback_existing_user(self, mock_verify_token, mock_post):
        """
        Test the callback for an existing user.
        """
        email = "test@example.com"
        first_name = "Test"
        last_name = "User"
        User.objects.create_user(username=email, email=email, password="password")

        # Mock the response from Google's token endpoint
        mock_post.return_value = MagicMock(
            json=lambda: {"id_token": "fake_id_token"}
        )

        # Mock the decoded token
        mock_verify_token.return_value = {
            "email": email,
            "given_name": first_name,
            "family_name": last_name,
        }

        initial_user_count = User.objects.count()
        response = self.client.get(self.callback_url + "?code=fake_code")

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn(settings.FRONTEND_URL, response.url)
        self.assertIn("access_token", response.url)
        self.assertIn("refresh_token", response.url)
        self.assertEqual(User.objects.count(), initial_user_count)

    @patch("users.views.requests.post")
    @patch("users.services.google_id_token.verify_oauth2_token")
    def test_google_login_callback_new_user(self, mock_verify_token, mock_post):
        """
        Test the callback for a new user.
        """
        email = "newuser@example.com"
        first_name = "New"
        last_name = "User"

        mock_post.return_value = MagicMock(
            json=lambda: {"id_token": "fake_id_token"}
        )

        mock_verify_token.return_value = {
            "email": email,
            "given_name": first_name,
            "family_name": last_name,
        }

        initial_user_count = User.objects.count()
        response = self.client.get(self.callback_url + "?code=fake_code")

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn(settings.FRONTEND_URL, response.url)
        self.assertIn("access_token", response.url)
        self.assertIn("refresh_token", response.url)
        self.assertEqual(User.objects.count(), initial_user_count + 1)
        new_user = User.objects.get(email=email)
        self.assertEqual(new_user.first_name, first_name)
        self.assertEqual(new_user.last_name, last_name)

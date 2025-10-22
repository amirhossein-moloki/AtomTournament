import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def api_client():
    """A pytest fixture that provides an instance of DRF's APIClient."""
    return APIClient()


@pytest.fixture
def create_user():
    """A pytest fixture to create a user."""

    def _create_user(username="testuser", password="password", phone_number="+1234567890"):
        return User.objects.create_user(
            username=username, password=password, phone_number=phone_number
        )

    return _create_user


@pytest.fixture
def authenticated_client(api_client, create_user):
    """A pytest fixture for an authenticated client."""
    user = create_user()
    api_client.force_authenticate(user=user)
    return api_client

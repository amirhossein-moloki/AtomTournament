"""
This file contains shared fixtures for the test suite.
Fixtures defined here are available to all tests in the project.
"""

import pytest
from unittest.mock import MagicMock, patch
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    """
    Configure the test database.
    This fixture runs once per session and ensures that the database is
    set up correctly for the test suite. It uses an in-memory SQLite
    database for speed.
    """
    with django_db_blocker.unblock():
        # You can add any one-time setup here if needed,
        # like loading initial data fixtures.
        pass


@pytest.fixture(autouse=True)
def override_settings(settings):
    """
    Override Django settings for the test environment.
    This fixture runs for every test and ensures that settings are
    optimized for testing.
    """
    settings.PASSWORD_HASHERS = [
        'django.contrib.auth.hashers.MD5PasswordHasher',
    ]
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        },
    }


@pytest.fixture
def api_client():
    """A pytest fixture that provides an instance of DRF's APIClient."""
    return APIClient()


@pytest.fixture
def user_factory(db):
    """A pytest fixture (factory) to create a user."""

    def _create_user(**kwargs):
        defaults = {
            "username": "testuser",
            "password": "password",
            "phone_number": "+989123456789",
        }
        defaults.update(kwargs)
        # Ensure we handle the case where username is passed as None
        if 'username' in defaults and defaults['username'] is None:
             defaults['username'] = f"user_{User.objects.count()}"

        user = User.objects.create_user(**defaults)
        return user

    return _create_user


@pytest.fixture
def default_user(user_factory):
    """A fixture to get a standard user instance."""
    return user_factory()


@pytest.fixture
def admin_user(user_factory):
    """A fixture to create an admin user."""
    return user_factory(
        username="adminuser",
        is_staff=True,
        is_superuser=True,
    )


@pytest.fixture
def authenticated_client(api_client, default_user):
    """A pytest fixture for an authenticated client with a standard user."""
    api_client.force_authenticate(user=default_user)
    return api_client


@pytest.fixture
def authenticated_admin_client(api_client, admin_user):
    """A pytest fixture for an authenticated client with an admin user."""
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def mock_zibal_service():
    """
    Mocks the ZibalService to prevent real API calls during tests.
    It's crucial to patch where the object is looked up ('wallet.views.ZibalService'),
    not where it's defined.
    """
    with patch('wallet.views.ZibalService') as mock:
        instance = mock.return_value
        instance.create_payment.return_value = {'trackId': '123456'}
        instance.verify_payment.return_value = {'result': 100, 'refNumber': 'ABCDEFG'}
        instance.inquiry_payment.return_value = {'result': 100, 'status': 1, 'refNumber': 'inquiry_ref_123'}
        instance.generate_payment_url.return_value = "https://gateway.zibal.ir/start/123456"
        yield mock


@pytest.fixture(autouse=True)
def mock_celery_tasks():
    """
    Mocks Celery tasks to prevent them from running during tests.
    This uses CELERY_TASK_ALWAYS_EAGER=True set in override_settings.
    If you need to mock specific tasks, you can do it here.
    """
    # Example of mocking a specific task if needed:
    # with patch('tournaments.tasks.process_tournament.delay') as mock_task:
    #     yield mock_task
    # For now, eager execution is enough.
    yield

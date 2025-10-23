"""
Tests for the rewards API endpoints in rewards/views.py.
These tests cover scenarios for claiming rewards and handling various
success and failure conditions.
"""
import pytest
from unittest.mock import patch
from django.urls import reverse
from rest_framework import status
from rewards.models import Wheel, Prize
from tournaments.models import Rank
from users.models import User


@pytest.fixture
def basic_rank(db):
    """Creates a basic rank."""
    return Rank.objects.create(name="Bronze", required_score=0)


@pytest.fixture
def advanced_rank(db):
    """Creates an advanced rank."""
    return Rank.objects.create(name="Gold", required_score=1000)


@pytest.fixture
def wheel_with_prizes(db, basic_rank):
    """Creates a wheel with a couple of prizes."""
    wheel = Wheel.objects.create(name="Daily Wheel", required_rank=basic_rank)
    prize1 = Prize.objects.create(wheel=wheel, name="10 Coins", chance=0.7)
    prize2 = Prize.objects.create(wheel=wheel, name="50 Coins", chance=0.3)
    return wheel, prize1, prize2


@pytest.fixture
def user_with_rank(default_user, basic_rank):
    """Associates a user with a rank."""
    default_user.rank = basic_rank
    default_user.save()
    return default_user


@pytest.mark.django_db
class TestWheelViewSet:
    def test_spin_wheel_success(
        self, authenticated_client, user_with_rank, wheel_with_prizes
    ):
        """
        GIVEN a user with the required rank
        WHEN they spin a wheel
        THEN a Spin object should be created with a determined prize.
        """
        wheel, prize1, _ = wheel_with_prizes
        url = reverse("wheel-spin", kwargs={"pk": wheel.pk})

        # Mock random.choices to always return the first prize
        with patch("random.choices", return_value=[prize1]) as mock_choices:
            response = authenticated_client.post(url)

            assert response.status_code == status.HTTP_200_OK
            assert response.data["prize"]["name"] == prize1.name
            mock_choices.assert_called_once()
            assert wheel.spins.filter(user=user_with_rank).exists()

    def test_spin_wheel_already_spun(
        self, authenticated_client, user_with_rank, wheel_with_prizes
    ):
        """
        GIVEN a user who has already spun a wheel
        WHEN they try to spin it again
        THEN they should receive a 403 Forbidden error.
        """
        wheel, prize1, _ = wheel_with_prizes
        # User spins the wheel once
        wheel.spins.create(user=user_with_rank, prize=prize1)

        url = reverse("wheel-spin", kwargs={"pk": wheel.pk})
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "already spun this wheel" in response.data["error"]

    def test_spin_wheel_insufficient_rank(
        self, authenticated_client, user_with_rank, wheel_with_prizes, advanced_rank
    ):
        """
        GIVEN a user whose rank is too low for a wheel
        WHEN they try to spin it
        THEN they should receive a 403 Forbidden error.
        """
        wheel, _, _ = wheel_with_prizes
        wheel.required_rank = advanced_rank
        wheel.save()

        url = reverse("wheel-spin", kwargs={"pk": wheel.pk})
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "required rank" in response.data["error"]

    def test_spin_wheel_no_prizes(self, authenticated_client, user_with_rank, basic_rank):
        """
        GIVEN a wheel with no prizes configured
        WHEN a user tries to spin it
        THEN they should receive a 400 Bad Request error.
        """
        wheel = Wheel.objects.create(name="Empty Wheel", required_rank=basic_rank)
        url = reverse("wheel-spin", kwargs={"pk": wheel.pk})
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "no prizes" in response.data["error"]

    def test_list_wheels_unauthenticated(self, api_client):
        """
        GIVEN an unauthenticated user
        WHEN they try to list wheels
        THEN they should receive a 401 Unauthorized error.
        """
        url = reverse("wheel-list")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

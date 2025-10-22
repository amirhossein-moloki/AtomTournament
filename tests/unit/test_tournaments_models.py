from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from tournaments.models import Game, Tournament
from users.models import User


@pytest.fixture
def game():
    """Fixture to create a Game instance."""
    return Game.objects.create(name="Test Game")


@pytest.fixture
def user():
    """Fixture to create a User instance."""
    return User.objects.create_user(
        username="testuser", password="password", phone_number="+123"
    )


@pytest.mark.django_db
def test_tournament_creation(game):
    """
    Test that a tournament can be created with valid data.
    """
    start_date = timezone.now() + timedelta(days=1)
    end_date = timezone.now() + timedelta(days=2)
    tournament = Tournament.objects.create(
        name="Test Tournament",
        game=game,
        start_date=start_date,
        end_date=end_date,
    )
    assert tournament.name == "Test Tournament"
    assert tournament.game == game


@pytest.mark.django_db
def test_end_date_before_start_date_fails(game):
    """
    Test that tournament creation fails if end_date is before start_date.
    """
    start_date = timezone.now() + timedelta(days=2)
    end_date = timezone.now() + timedelta(days=1)
    with pytest.raises(ValidationError):
        tournament = Tournament(
            name="Test Tournament",
            game=game,
            start_date=start_date,
            end_date=end_date,
        )
        tournament.clean()


@pytest.mark.django_db
def test_paid_tournament_requires_entry_fee(game):
    """
    Test that a paid tournament must have an entry fee.
    """
    start_date = timezone.now() + timedelta(days=1)
    end_date = timezone.now() + timedelta(days=2)
    with pytest.raises(ValidationError):
        tournament = Tournament(
            name="Test Tournament",
            game=game,
            start_date=start_date,
            end_date=end_date,
            is_free=False,
        )
        tournament.clean()

import pytest
from rest_framework import status
from tournaments.models import Game, Tournament
from users.models import User


@pytest.mark.django_db
def test_user_join_tournament_flow(authenticated_client, game, user):
    """
    Test a simple end-to-end user flow of joining a tournament.
    """
    tournament = Tournament.objects.create(
        name="E2E Test Tournament",
        game=game,
        start_date="2025-10-22T12:00:00Z",
        end_date="2025-10-23T12:00:00Z",
    )

    # Join the tournament
    response = authenticated_client.post(
        f"/api/tournaments/tournaments/{tournament.id}/join/"
    )
    assert response.status_code == status.HTTP_201_CREATED

    # Verify the user is a participant
    tournament.refresh_from_db()
    assert tournament.participants.filter(id=user.id).exists()

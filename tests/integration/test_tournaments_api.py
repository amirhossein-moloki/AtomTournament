from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework import status

from tournaments.models import Game, Tournament, TournamentColor
from users.models import User, Team
from verification.models import Verification


@pytest.fixture
def game():
    return Game.objects.create(name="Test Game")


@pytest.fixture
def user():
    user = User.objects.create_user(
        username="testuser", password="password", phone_number="+123"
    )
    Verification.objects.create(user=user, level=2)
    return user


@pytest.fixture
def admin_user():
    return User.objects.create_superuser(
        username="admin", password="password", phone_number="+456"
    )


@pytest.fixture
def tournament(game):
    return Tournament.objects.create(
        name="Test Tournament",
        game=game,
        start_date=timezone.now() + timedelta(days=1),
        end_date=timezone.now() + timedelta(days=2),
    )


@pytest.mark.django_db
class TestTournamentViewSet:
    def test_list_tournaments_unauthenticated(self, api_client, tournament):
        response = api_client.get("/api/tournaments/tournaments/")
        assert response.status_code == status.HTTP_200_OK

    def test_list_tournaments_authenticated(self, authenticated_client, tournament):
        response = authenticated_client.get("/api/tournaments/tournaments/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert len(response.data["results"]) == 1

    def test_create_tournament_by_admin(self, api_client, admin_user, game):
        api_client.force_authenticate(user=admin_user)
        color = TournamentColor.objects.create(name="Red", rgb_code="255,0,0")
        data = {
            "name": "New Tournament by Admin",
            "game": game.id,
            "color": color.id,
            "start_date": timezone.now() + timedelta(days=3),
            "end_date": timezone.now() + timedelta(days=4),
        }
        response = api_client.post("/api/tournaments/tournaments/", data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Tournament.objects.filter(
            name="New Tournament by Admin", color=color
        ).exists()

    def test_create_tournament_by_non_admin_fails(self, authenticated_client, game):
        data = {
            "name": "New Tournament by User",
            "game": game.id,
            "start_date": timezone.now() + timedelta(days=3),
            "end_date": timezone.now() + timedelta(days=4),
        }
        response = authenticated_client.post("/api/tournaments/tournaments/", data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_join_individual_tournament(self, api_client, user, tournament):
        api_client.force_authenticate(user=user)
        response = api_client.post(f"/api/tournaments/tournaments/{tournament.id}/join/")
        assert response.status_code == status.HTTP_201_CREATED
        assert tournament.participants.filter(id=user.id).exists()

    @patch("tournaments.services.send_email_notification.delay")
    @patch("tournaments.services.send_sms_notification.delay")
    def test_join_team_tournament(
        self, mock_send_sms, mock_send_email, api_client, user, game
    ):
        team = Team.objects.create(name="Team For Tourney", captain=user)
        team_tournament = Tournament.objects.create(
            name="Team Tournament",
            game=game,
            start_date=timezone.now() + timedelta(days=1),
            end_date=timezone.now() + timedelta(days=2),
            type="team",
            team_size=1,
        )
        api_client.force_authenticate(user=user)
        data = {"team_id": team.id, "member_ids": [user.id]}
        response = api_client.post(
            f"/api/tournaments/tournaments/{team_tournament.id}/join/", data
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert team_tournament.teams.filter(id=team.id).exists()
        mock_send_email.assert_called_once()
        mock_send_sms.assert_called()

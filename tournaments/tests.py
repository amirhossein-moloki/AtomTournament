from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Tournament, Game, Rank, Match
from users.models import User, Team
from verification.models import Verification
from django.utils import timezone
from tournament_project.celery import app as celery_app
from datetime import timedelta
from django.core.exceptions import ValidationError

class TournamentModelTests(TestCase):
    def setUp(self):
        self.game = Game.objects.create(name="Test Game")
        self.user = User.objects.create_user(username="testuser", password="password", phone_number="+123")
        self.start_date = timezone.now() + timedelta(days=1)
        self.end_date = timezone.now() + timedelta(days=2)

    def test_tournament_creation(self):
        """
        Test that a tournament can be created with valid data.
        """
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game=self.game,
            start_date=self.start_date,
            end_date=self.end_date,
        )
        self.assertEqual(tournament.name, "Test Tournament")
        self.assertEqual(tournament.game, self.game)

    def test_end_date_before_start_date_fails(self):
        """
        Test that tournament creation fails if end_date is before start_date.
        """
        with self.assertRaises(ValidationError):
            tournament = Tournament(
                name="Test Tournament",
                game=self.game,
                start_date=self.end_date,
                end_date=self.start_date,
            )
            tournament.clean()

    def test_paid_tournament_requires_entry_fee(self):
        """
        Test that a paid tournament must have an entry fee.
        """
        with self.assertRaises(ValidationError):
            tournament = Tournament(
                name="Test Tournament",
                game=self.game,
                start_date=self.start_date,
                end_date=self.end_date,
                is_free=False,
            )
            tournament.clean()

    def test_distribute_scores_individual(self):
        """
        Test the score distribution for an individual tournament.
        """
        tournament = Tournament.objects.create(
            name="Test Tournament",
            game=self.game,
            start_date=self.start_date,
            end_date=self.end_date,
            type="individual",
        )
        p1 = User.objects.create_user(username="p1", password="p", phone_number="+1")
        p2 = User.objects.create_user(username="p2", password="p", phone_number="+2")
        tournament.top_players.add(p1, p2)

        initial_score_p1 = p1.score
        initial_score_p2 = p2.score

        tournament.distribute_scores()
        p1.refresh_from_db()
        p2.refresh_from_db()

        self.assertEqual(p1.score, initial_score_p1 + 5)
        self.assertEqual(p2.score, initial_score_p2 + 4)


class MatchModelTests(TestCase):
    def test_match_creation(self):
        # TODO: Write test for match creation
        pass


class TournamentViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.tournaments_url = "/api/tournaments/tournaments/"
        self.user = User.objects.create_user(username="user", password="password", phone_number="+1")
        self.admin_user = User.objects.create_superuser(
            username="admin", password="password", phone_number="+2"
        )
        Verification.objects.create(user=self.user, level=2)
        self.game = Game.objects.create(name="Test Game")
        self.tournament = Tournament.objects.create(
            name="Test Tournament",
            game=self.game,
            start_date=timezone.now() + timedelta(days=1),
            end_date=timezone.now() + timedelta(days=2),
        )
        self.old_eager = celery_app.conf.task_always_eager
        celery_app.conf.task_always_eager = True

    def tearDown(self):
        celery_app.conf.task_always_eager = self.old_eager

    def test_list_tournaments_unauthenticated(self):
        response = self.client.get(self.tournaments_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_tournaments_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.tournaments_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_tournament_by_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        data = {
            "name": "New Tournament by Admin",
            "game": self.game.id,
            "start_date": timezone.now() + timedelta(days=3),
            "end_date": timezone.now() + timedelta(days=4),
        }
        response = self.client.post(self.tournaments_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Tournament.objects.filter(name="New Tournament by Admin").exists())

    def test_create_tournament_by_non_admin_fails(self):
        self.client.force_authenticate(user=self.user)
        data = {
            "name": "New Tournament by User",
            "game": self.game.id,
            "start_date": timezone.now() + timedelta(days=3),
            "end_date": timezone.now() + timedelta(days=4),
        }
        response = self.client.post(self.tournaments_url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_join_individual_tournament(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(f"{self.tournaments_url}{self.tournament.id}/join/")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(self.tournament.participants.filter(id=self.user.id).exists())

    def test_join_team_tournament(self):
        team = Team.objects.create(name="Team For Tourney", captain=self.user)
        team_tournament = Tournament.objects.create(
            name="Team Tournament",
            game=self.game,
            start_date=timezone.now() + timedelta(days=1),
            end_date=timezone.now() + timedelta(days=2),
            type="team",
        )
        self.client.force_authenticate(user=self.user)
        data = {"team_id": team.id, "member_ids": [self.user.id]}
        response = self.client.post(f"{self.tournaments_url}{team_tournament.id}/join/", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(team_tournament.teams.filter(id=team.id).exists())

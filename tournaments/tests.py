from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from .models import Tournament, Game, Match, Participant, Report, WinnerSubmission, GameManager
from users.models import User, Team
from verification.models import Verification
from django.utils import timezone
from tournament_project.celery import app as celery_app
from datetime import timedelta
from django.core.exceptions import ValidationError
from .services import (
    join_tournament,
    confirm_match_result,
    generate_matches,
    create_report_service,
    resolve_report_service,
    reject_report_service,
    create_winner_submission_service,
    approve_winner_submission_service,
    reject_winner_submission_service,
)
from .exceptions import ApplicationError
from unittest.mock import patch


class TournamentModelTests(TestCase):
    def setUp(self):
        self.game = Game.objects.create(name="Test Game")
        self.user = User.objects.create_user(
            username="testuser", password="password", phone_number="+123"
        )
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
    def setUp(self):
        self.game = Game.objects.create(name="Test Game")
        self.user1 = User.objects.create_user(
            username="user1", password="p", phone_number="+201"
        )
        self.user2 = User.objects.create_user(
            username="user2", password="p", phone_number="+202"
        )
        self.tournament = Tournament.objects.create(
            name="Test Tournament",
            game=self.game,
            start_date=timezone.now() + timedelta(days=1),
            end_date=timezone.now() + timedelta(days=2),
        )

    def test_match_creation(self):
        """Test that a Match object can be created successfully."""
        match = Match.objects.create(
            tournament=self.tournament,
            participant1_user=self.user1,
            participant2_user=self.user2,
            round=1,
            match_type="individual",
        )
        self.assertEqual(match.tournament, self.tournament)
        self.assertEqual(match.round, 1)
        self.assertEqual(Match.objects.count(), 1)


class TournamentViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.tournaments_url = "/api/tournaments/"
        self.user = User.objects.create_user(
            username="user", password="password", phone_number="+1"
        )
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
        response = self.client.get(f"{self.tournaments_url}tournaments/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_tournaments_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"{self.tournaments_url}tournaments/")
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
        response = self.client.post(f"{self.tournaments_url}tournaments/", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Tournament.objects.filter(name="New Tournament by Admin").exists()
        )

    def test_create_tournament_by_non_admin_fails(self):
        self.client.force_authenticate(user=self.user)
        data = {
            "name": "New Tournament by User",
            "game": self.game.id,
            "start_date": timezone.now() + timedelta(days=3),
            "end_date": timezone.now() + timedelta(days=4),
        }
        response = self.client.post(f"{self.tournaments_url}tournaments/", data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_join_individual_tournament(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(f"{self.tournaments_url}tournaments/{self.tournament.id}/join/")
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
        response = self.client.post(
            f"{self.tournaments_url}tournaments/{team_tournament.id}/join/", data
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(team_tournament.teams.filter(id=team.id).exists())

    def test_generate_matches(self):
        self.client.force_authenticate(user=self.admin_user)
        p1 = User.objects.create_user(username="p1", password="p", phone_number="+3")
        p2 = User.objects.create_user(username="p2", password="p", phone_number="+4")
        self.tournament.participants.add(p1, p2)
        response = self.client.post(
            f"{self.tournaments_url}tournaments/{self.tournament.id}/generate_matches/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.tournament.matches.count(), 1)

    @patch("tournaments.views.send_tournament_credentials.apply_async")
    def test_start_countdown(self, mock_apply_async):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            f"{self.tournaments_url}tournaments/{self.tournament.id}/start_countdown/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.tournament.refresh_from_db()
        self.assertIsNotNone(self.tournament.countdown_start_time)
        mock_apply_async.assert_called_once()


class MatchViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.matches_url = "/api/tournaments/matches/"
        self.user1 = User.objects.create_user(
            username="user1", password="p", phone_number="+201"
        )
        self.user2 = User.objects.create_user(
            username="user2", password="p", phone_number="+202"
        )
        self.game = Game.objects.create(name="Test Game")
        self.tournament = Tournament.objects.create(
            name="Test Tournament",
            game=self.game,
            start_date=timezone.now() + timedelta(days=1),
            end_date=timezone.now() + timedelta(days=2),
        )
        self.match = Match.objects.create(
            tournament=self.tournament,
            participant1_user=self.user1,
            participant2_user=self.user2,
            round=1,
        )

    def test_confirm_result(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(
            f"{self.matches_url}{self.match.id}/confirm_result/",
            {"winner_id": self.user1.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.match.refresh_from_db()
        self.assertTrue(self.match.is_confirmed)
        self.assertEqual(self.match.winner_user, self.user1)

    def test_dispute_result(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(
            f"{self.matches_url}{self.match.id}/dispute_result/",
            {"reason": "He cheated!"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.match.refresh_from_db()
        self.assertTrue(self.match.is_disputed)


class ReportViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.reports_url = "/api/tournaments/reports/"
        self.reporter = User.objects.create_user(
            username="reporter", password="p", phone_number="+301"
        )
        self.reported = User.objects.create_user(
            username="reported", password="p", phone_number="+302"
        )
        self.admin_user = User.objects.create_superuser(
            username="admin", password="p", phone_number="+303"
        )
        self.game = Game.objects.create(name="Test Game")
        self.tournament = Tournament.objects.create(
            name="T",
            game=self.game,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=1),
            is_free=False,
            entry_fee=100,
        )
        self.match = Match.objects.create(
            tournament=self.tournament,
            round=1,
            participant1_user=self.reporter,
            participant2_user=self.reported,
        )

    def test_create_report(self):
        self.client.force_authenticate(user=self.reporter)
        data = {
            "reported_user": self.reported.id,
            "match": self.match.id,
            "description": "He was rude.",
        }
        response = self.client.post(self.reports_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Report.objects.filter(reporter=self.reporter, reported_user=self.reported).exists()
        )

    def test_resolve_report(self):
        report = Report.objects.create(
            reporter=self.reporter,
            reported_user=self.reported,
            match=self.match,
            description="d",
        )
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(f"{self.reports_url}{report.id}/resolve/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        report.refresh_from_db()
        self.assertEqual(report.status, "resolved")

    def test_reject_report(self):
        report = Report.objects.create(
            reporter=self.reporter,
            reported_user=self.reported,
            match=self.match,
            description="d",
        )
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(f"{self.reports_url}{report.id}/reject/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        report.refresh_from_db()
        self.assertEqual(report.status, "rejected")


from io import BytesIO
from PIL import Image

class WinnerSubmissionViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.submissions_url = "/api/tournaments/winner-submissions/"
        self.winner = User.objects.create_user(
            username="winner", password="p", phone_number="+401"
        )
        self.admin_user = User.objects.create_superuser(
            username="admin", password="p", phone_number="+402"
        )
        self.game = Game.objects.create(name="Test Game")
        self.tournament = Tournament.objects.create(
            name="T",
            game=self.game,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=1),
            is_free=False,
            entry_fee=100,
        )

    def _generate_dummy_image(self, name="test.png"):
        file = BytesIO()
        image = Image.new("RGB", (10, 10), "white")
        image.save(file, "png")
        file.name = name
        file.seek(0)
        return SimpleUploadedFile(name, file.read(), content_type="image/png")

    @patch("tournaments.services.get_tournament_winners")
    def test_create_submission(self, mock_get_winners):
        mock_get_winners.return_value = [self.winner]
        self.client.force_authenticate(user=self.winner)
        data = {
            "tournament": self.tournament.id,
            "video": self._generate_dummy_image("video.mp4"),
        }
        response = self.client.post(self.submissions_url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            WinnerSubmission.objects.filter(
                winner=self.winner, tournament=self.tournament
            ).exists()
        )

    def test_approve_submission(self):
        submission = WinnerSubmission.objects.create(
            winner=self.winner, tournament=self.tournament, video="v.mp4"
        )
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(f"{self.submissions_url}{submission.id}/approve/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        submission.refresh_from_db()
        self.assertEqual(submission.status, "approved")

    def test_reject_submission(self):
        submission = WinnerSubmission.objects.create(
            winner=self.winner, tournament=self.tournament, video="v.mp4"
        )
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(f"{self.submissions_url}{submission.id}/reject/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        submission.refresh_from_db()
        self.assertEqual(submission.status, "rejected")


class GameManagerPermissionsTests(APITestCase):
    def setUp(self):
        self.client = APIClient()

        # Games
        self.managed_game = Game.objects.create(name="Managed Game")
        self.other_game = Game.objects.create(name="Other Game")

        # Users
        self.admin_user = User.objects.create_superuser(
            username="admin", password="password", phone_number="+1"
        )
        self.game_manager = User.objects.create_user(
            username="gamemanager", password="password", phone_number="+2"
        )
        self.regular_user = User.objects.create_user(
            username="regularuser", password="password", phone_number="+3"
        )

        # Assign manager to the game
        GameManager.objects.create(user=self.game_manager, game=self.managed_game)

        # A tournament that belongs to the managed game
        self.tournament_in_managed_game = Tournament.objects.create(
            name="Tournament in Managed Game",
            game=self.managed_game,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=1),
        )

        self.tournaments_url = "/api/tournaments/tournaments/"
        self.tournament_detail_url = f"{self.tournaments_url}{self.tournament_in_managed_game.id}/"

    def test_manager_can_create_tournament_for_managed_game(self):
        """A game manager should be able to create a tournament for their game."""
        self.client.force_authenticate(user=self.game_manager)
        data = {
            "name": "New Tournament by Manager",
            "game": self.managed_game.id,
            "start_date": timezone.now() + timedelta(days=2),
            "end_date": timezone.now() + timedelta(days=3),
        }
        response = self.client.post(self.tournaments_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Tournament.objects.filter(name="New Tournament by Manager").exists())

    def test_manager_cannot_create_tournament_for_other_game(self):
        """A game manager should NOT be able to create a tournament for another game."""
        self.client.force_authenticate(user=self.game_manager)
        data = {
            "name": "Illegal Tournament",
            "game": self.other_game.id,
            "start_date": timezone.now() + timedelta(days=2),
            "end_date": timezone.now() + timedelta(days=3),
        }
        response = self.client.post(self.tournaments_url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_update_tournament_in_managed_game(self):
        """A game manager should be able to update a tournament in their game."""
        self.client.force_authenticate(user=self.game_manager)
        data = {"name": "Updated Name"}
        response = self.client.patch(self.tournament_detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.tournament_in_managed_game.refresh_from_db()
        self.assertEqual(self.tournament_in_managed_game.name, "Updated Name")

    def test_manager_cannot_update_tournament_in_other_game(self):
        """A game manager should NOT be able to update a tournament in another game."""
        other_tournament = Tournament.objects.create(
            name="Tournament in Other Game",
            game=self.other_game,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=1),
        )
        self.client.force_authenticate(user=self.game_manager)
        data = {"name": "Updated Name"}
        response = self.client.patch(f"{self.tournaments_url}{other_tournament.id}/", data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_regular_user_cannot_create_tournament(self):
        """A regular user should NOT be able to create a tournament."""
        self.client.force_authenticate(user=self.regular_user)
        data = {
            "name": "Tournament by Regular User",
            "game": self.managed_game.id,
            "start_date": timezone.now() + timedelta(days=2),
            "end_date": timezone.now() + timedelta(days=3),
        }
        response = self.client.post(self.tournaments_url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

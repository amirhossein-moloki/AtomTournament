from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Tournament, Game, Rank, Match, Participant
from users.models import User, Team
from wallet.models import Wallet
from verification.models import Verification
from django.utils import timezone
from tournament_project.celery import app as celery_app
from datetime import timedelta
from django.core.exceptions import ValidationError
from .services import (
    join_tournament, confirm_match_result,
    create_report_service, resolve_report_service, reject_report_service,
    create_winner_submission_service, approve_winner_submission_service, reject_winner_submission_service
)
from .exceptions import ApplicationError
from .models import Report, WinnerSubmission
from unittest.mock import patch

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
    def setUp(self):
        self.game = Game.objects.create(name="Test Game")
        self.user1 = User.objects.create_user(username="user1", password="p", phone_number="+201")
        self.user2 = User.objects.create_user(username="user2", password="p", phone_number="+202")
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


class TournamentServiceTests(TestCase):
    def setUp(self):
        self.game = Game.objects.create(name="Test Game")
        self.user = User.objects.create_user(username="testuser", password="password", phone_number="+12345")
        self.wallet = self.user.wallet
        self.wallet.withdrawable_balance = 100
        self.wallet.save()
        self.tournament = Tournament.objects.create(
            name="Test Tournament",
            game=self.game,
            start_date=timezone.now() + timedelta(days=1),
            end_date=timezone.now() + timedelta(days=2),
            is_free=False,
            entry_fee=50,
            required_verification_level=1,
        )
        Verification.objects.create(user=self.user, level=1)

    def test_join_individual_tournament_success(self):
        """
        Test that a user can successfully join an individual tournament.
        """
        participant = join_tournament(tournament=self.tournament, user=self.user)
        self.wallet.refresh_from_db()
        self.assertIsInstance(participant, Participant)
        self.assertTrue(self.tournament.participants.filter(id=self.user.id).exists())
        self.assertEqual(self.wallet.withdrawable_balance, 50)

    def test_join_insufficient_funds_fails(self):
        """
        Test that joining a paid tournament fails if the user has insufficient funds.
        """
        self.wallet.withdrawable_balance = 20
        self.wallet.save()
        with self.assertRaisesMessage(ApplicationError, "Insufficient funds to join the tournament."):
            join_tournament(tournament=self.tournament, user=self.user)

    def test_join_already_joined_fails(self):
        """
        Test that a user cannot join a tournament they are already in.
        """
        join_tournament(tournament=self.tournament, user=self.user)
        with self.assertRaisesMessage(ApplicationError, "You have already joined this tournament."):
            join_tournament(tournament=self.tournament, user=self.user)

    def test_join_insufficient_verification_fails(self):
        """
        Test that joining fails if the user's verification level is too low.
        """
        self.tournament.required_verification_level = 2
        self.tournament.save()
        with self.assertRaisesMessage(ApplicationError, "You do not have the required verification level to join this tournament."):
            join_tournament(tournament=self.tournament, user=self.user)

    def test_join_team_tournament_success(self):
        """
        Test that a team can successfully join a team tournament.
        """
        captain = self.user
        member = User.objects.create_user(username="member", password="p", phone_number="+54321")

        captain.wallet.withdrawable_balance = 100
        captain.wallet.save()
        member.wallet.withdrawable_balance = 100
        member.wallet.save()

        Verification.objects.create(user=member, level=1)

        team = Team.objects.create(name="Test Team", captain=captain)
        team.members.add(captain, member)

        team_tournament = Tournament.objects.create(
            name="Team Tournament",
            game=self.game,
            start_date=timezone.now() + timedelta(days=1),
            end_date=timezone.now() + timedelta(days=2),
            is_free=False,
            entry_fee=50,
            type="team",
            required_verification_level=1,
        )

        result_team = join_tournament(
            tournament=team_tournament,
            user=captain,
            team_id=team.id,
            member_ids=[captain.id, member.id]
        )

        self.assertEqual(result_team, team)
        self.assertTrue(team_tournament.teams.filter(id=team.id).exists())

        captain.wallet.refresh_from_db()
        member.wallet.refresh_from_db()
        self.assertEqual(captain.wallet.withdrawable_balance, 50)
        self.assertEqual(member.wallet.withdrawable_balance, 50)


class MatchServiceTests(TestCase):
    def setUp(self):
        self.game = Game.objects.create(name="Test Game")
        self.user1 = User.objects.create_user(username="user1", password="p", phone_number="+201")
        self.user2 = User.objects.create_user(username="user2", password="p", phone_number="+202")
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

    def test_confirm_match_result_success(self):
        """
        Test that confirming a match result works correctly.
        """
        confirm_match_result(self.match, winner_id=self.user1.id)
        self.match.refresh_from_db()
        self.assertTrue(self.match.is_confirmed)
        self.assertEqual(self.match.winner_user, self.user1)

    def test_confirm_match_result_invalid_winner_id_fails(self):
        """
        Test that confirming with an invalid winner ID raises an error.
        """
        invalid_winner_id = 9999
        with self.assertRaisesMessage(ApplicationError, "Invalid winner ID."):
            confirm_match_result(self.match, winner_id=invalid_winner_id)


@patch("tournaments.services.send_notification")
class ReportServiceTests(TestCase):
    def setUp(self):
        self.reporter = User.objects.create_user(username="reporter", password="p", phone_number="+301")
        self.reported = User.objects.create_user(username="reported", password="p", phone_number="+302")
        self.game = Game.objects.create(name="Test Game")
        self.tournament = Tournament.objects.create(name="T", game=self.game, start_date=timezone.now(), end_date=timezone.now() + timedelta(days=1))
        self.match = Match.objects.create(tournament=self.tournament, round=1, participant1_user=self.reporter, participant2_user=self.reported)

    def test_create_report_service_success(self, mock_send_notification):
        report = create_report_service(
            reporter=self.reporter,
            reported_user_id=self.reported.id,
            match_id=self.match.id,
            description="He was rude."
        )
        self.assertIsInstance(report, Report)
        self.assertEqual(report.status, "pending")
        mock_send_notification.assert_called_once()

    def test_resolve_report_service_no_ban(self, mock_send_notification):
        report = Report.objects.create(reporter=self.reporter, reported_user=self.reported, match=self.match, description="d")
        resolve_report_service(report, ban_user=False)
        report.refresh_from_db()
        self.assertEqual(report.status, "resolved")
        self.assertTrue(report.reported_user.is_active)
        mock_send_notification.assert_called_once()

    def test_resolve_report_service_with_ban(self, mock_send_notification):
        report = Report.objects.create(reporter=self.reporter, reported_user=self.reported, match=self.match, description="d")
        resolve_report_service(report, ban_user=True)
        report.refresh_from_db()
        self.reported.refresh_from_db()
        self.assertEqual(report.status, "resolved")
        self.assertFalse(self.reported.is_active)
        mock_send_notification.assert_called_once()

    def test_reject_report_service(self, mock_send_notification):
        report = Report.objects.create(reporter=self.reporter, reported_user=self.reported, match=self.match, description="d")
        reject_report_service(report)
        report.refresh_from_db()
        self.assertEqual(report.status, "rejected")
        mock_send_notification.assert_called_once()


@patch("tournaments.services.send_notification")
class WinnerSubmissionServiceTests(TestCase):
    def setUp(self):
        self.winner = User.objects.create_user(username="winner", password="p", phone_number="+401")
        self.game = Game.objects.create(name="Test Game")
        self.tournament = Tournament.objects.create(name="T", game=self.game, start_date=timezone.now(), end_date=timezone.now() + timedelta(days=1))

    @patch("tournaments.services.get_tournament_winners")
    def test_create_winner_submission_service_success(self, mock_get_winners, mock_send_notification):
        mock_get_winners.return_value = [self.winner]
        submission = create_winner_submission_service(user=self.winner, tournament=self.tournament, video="video.mp4")
        self.assertIsInstance(submission, WinnerSubmission)
        mock_send_notification.assert_called_once()

    @patch("tournaments.services.get_tournament_winners")
    def test_create_winner_submission_not_a_winner_fails(self, mock_get_winners, mock_send_notification):
        loser = User.objects.create_user(username="loser", password="p", phone_number="+402")
        mock_get_winners.return_value = [self.winner]
        with self.assertRaisesMessage(ApplicationError, "You are not one of the top 5 winners."):
            create_winner_submission_service(user=loser, tournament=self.tournament, video="video.mp4")

    @patch("tournaments.services.pay_prize")
    def test_approve_winner_submission_service(self, mock_pay_prize, mock_send_notification):
        submission = WinnerSubmission.objects.create(winner=self.winner, tournament=self.tournament, video="v.mp4")
        approve_winner_submission_service(submission)
        submission.refresh_from_db()
        self.assertEqual(submission.status, "approved")
        mock_pay_prize.assert_called_once_with(self.tournament, self.winner)
        mock_send_notification.assert_called_once()

    @patch("tournaments.services.refund_entry_fees")
    def test_reject_winner_submission_service(self, mock_refund, mock_send_notification):
        submission = WinnerSubmission.objects.create(winner=self.winner, tournament=self.tournament, video="v.mp4")
        reject_winner_submission_service(submission)
        submission.refresh_from_db()
        self.assertEqual(submission.status, "rejected")
        mock_refund.assert_called_once_with(self.tournament, self.winner)
        mock_send_notification.assert_called_once()

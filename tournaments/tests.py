from datetime import timedelta
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from io import BytesIO

from PIL import Image
from rest_framework.test import APIClient, APITestCase

from tournament_project.celery import app as celery_app
from teams.models import Team, TeamMembership
from users.models import InGameID, User
from verification.models import Verification

from .models import (Game, GameManager, Match, Report, Tournament, TournamentColor,
                     TournamentImage, WinnerSubmission)
from .services import get_tournament_winners


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
        Test the score distribution for an individual tournament using the service.
        """
        from .services import distribute_scores_for_tournament

        tournament = Tournament.objects.create(
            name="Test Tournament",
            game=self.game,
            start_date=self.start_date,
            end_date=self.end_date,
            type="individual",
        )
        p1 = User.objects.create_user(
            username="p1", password="p", phone_number="+1", score=100
        )
        p2 = User.objects.create_user(
            username="p2", password="p", phone_number="+2", score=100
        )
        tournament.top_players.add(p1, p2)

        initial_score_p1 = p1.score
        initial_score_p2 = p2.score

        distribute_scores_for_tournament(tournament)

        p1.refresh_from_db()
        p2.refresh_from_db()

        # Default distribution is [5, 4, 3, 2, 1]
        self.assertEqual(p1.score, initial_score_p1 + 5)
        self.assertEqual(p2.score, initial_score_p2 + 4)

    def test_distribute_scores_team(self):
        """
        Test the score distribution for a team-based tournament.
        """
        from .services import distribute_scores_for_tournament

        tournament = Tournament.objects.create(
            name="Team Tournament",
            game=self.game,
            start_date=self.start_date,
            end_date=self.end_date,
            type="team",
        )
        captain1 = User.objects.create_user(
            username="c1", password="p", phone_number="+10", score=50
        )
        member1 = User.objects.create_user(
            username="m1", password="p", phone_number="+11", score=50
        )
        team1 = Team.objects.create(name="Team 1", captain=captain1)
        team1.members.add(member1)

        captain2 = User.objects.create_user(
            username="c2", password="p", phone_number="+20", score=50
        )
        team2 = Team.objects.create(name="Team 2", captain=captain2)

        tournament.top_teams.add(team1, team2)

        distribute_scores_for_tournament(tournament)

        captain1.refresh_from_db()
        member1.refresh_from_db()
        captain2.refresh_from_db()

        self.assertEqual(captain1.score, 50 + 5)
        self.assertEqual(member1.score, 50 + 5)  # Both members get points
        self.assertEqual(captain2.score, 50 + 4)

    def test_distribute_scores_custom_distribution(self):
        """
        Test score distribution with a custom list of scores.
        """
        from .services import distribute_scores_for_tournament

        tournament = Tournament.objects.create(
            name="Custom Score Tournament",
            game=self.game,
            start_date=self.start_date,
            end_date=self.end_date,
            type="individual",
        )
        p1 = User.objects.create_user(
            username="p1", password="p", phone_number="+1", score=0
        )
        tournament.top_players.add(p1)

        custom_scores = [100]
        distribute_scores_for_tournament(tournament, score_distribution=custom_scores)

        p1.refresh_from_db()
        self.assertEqual(p1.score, 100)


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
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_tournaments_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"{self.tournaments_url}tournaments/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)

    def test_create_tournament_by_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        color = TournamentColor.objects.create(name="Red", rgb_code="255,0,0")
        data = {
            "name": "New Tournament by Admin",
            "game": self.game.id,
            "color": color.id,
            "start_date": timezone.now() + timedelta(days=3),
            "end_date": timezone.now() + timedelta(days=4),
        }
        response = self.client.post(f"{self.tournaments_url}tournaments/", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Tournament.objects.filter(name="New Tournament by Admin", color=color).exists()
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
        response = self.client.post(
            f"{self.tournaments_url}tournaments/{self.tournament.id}/join/"
        )
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
            team_size=1,
        )
        self.client.force_authenticate(user=self.user)
        data = {"team_id": team.id, "member_ids": [self.user.id]}
        response = self.client.post(
            f"{self.tournaments_url}tournaments/{team_tournament.id}/join/", data
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(team_tournament.teams.filter(id=team.id).exists())

    def test_join_paid_individual_tournament(self):
        """
        Test that a user can join a paid individual tournament and the entry fee is deducted.
        """
        self.user.wallet.total_balance = 200
        self.user.wallet.withdrawable_balance = 200
        self.user.wallet.save()
        paid_tournament = Tournament.objects.create(
            name="Paid Tournament",
            game=self.game,
            start_date=timezone.now() + timedelta(days=1),
            end_date=timezone.now() + timedelta(days=2),
            is_free=False,
            entry_fee=100,
            type="individual",
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f"{self.tournaments_url}tournaments/{paid_tournament.id}/join/"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.user.refresh_from_db()
        self.assertEqual(self.user.wallet.withdrawable_balance, 100)
        self.assertTrue(
            paid_tournament.participants.filter(id=self.user.id).exists()
        )

    def test_join_paid_team_tournament(self):
        """
        Test that a user can join a paid team tournament and the entry fee is deducted.
        """
        self.user.wallet.total_balance = 200
        self.user.wallet.withdrawable_balance = 200
        self.user.wallet.save()
        team = Team.objects.create(name="Paid Team", captain=self.user)
        paid_tournament = Tournament.objects.create(
            name="Paid Team Tournament",
            game=self.game,
            start_date=timezone.now() + timedelta(days=1),
            end_date=timezone.now() + timedelta(days=2),
            is_free=False,
            entry_fee=50,
            type="team",
            team_size=1,
        )
        self.client.force_authenticate(user=self.user)
        data = {"team_id": team.id, "member_ids": [self.user.id]}
        response = self.client.post(
            f"{self.tournaments_url}tournaments/{paid_tournament.id}/join/", data
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.user.refresh_from_db()
        self.assertEqual(self.user.wallet.withdrawable_balance, 150)
        self.assertTrue(paid_tournament.teams.filter(id=team.id).exists())

    def test_join_paid_tournament_insufficient_balance(self):
        """
        Test that a user cannot join a paid tournament if they have insufficient balance.
        """
        self.user.wallet.total_balance = 50
        self.user.wallet.withdrawable_balance = 50
        self.user.wallet.save()
        paid_tournament = Tournament.objects.create(
            name="Expensive Tournament",
            game=self.game,
            start_date=timezone.now() + timedelta(days=1),
            end_date=timezone.now() + timedelta(days=2),
            is_free=False,
            entry_fee=100,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f"{self.tournaments_url}tournaments/{paid_tournament.id}/join/"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertEqual(self.user.wallet.withdrawable_balance, 50)
        self.assertFalse(
            paid_tournament.participants.filter(id=self.user.id).exists()
        )

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

    def test_default_ordering(self):
        # Create tournaments with different start dates
        now = timezone.now()
        Tournament.objects.create(
            name="Future Tournament",
            game=self.game,
            start_date=now + timedelta(days=10),
            end_date=now + timedelta(days=11),
        )
        Tournament.objects.create(
            name="Past Tournament",
            game=self.game,
            start_date=now - timedelta(days=10),
            end_date=now - timedelta(days=9),
        )
        self.client.force_authenticate(user=self.user)
        # Add status=all to include finished tournaments for ordering test
        response = self.client.get(f"{self.tournaments_url}tournaments/?status=all&ordering=start_date")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)  # 1 from setup, 2 from this test
        self.assertEqual(len(response.data["results"]), 3)
        # Check the order
        self.assertEqual(response.data["results"][0]["name"], "Past Tournament")
        self.assertEqual(response.data["results"][1]["name"], "Test Tournament")
        self.assertEqual(response.data["results"][2]["name"], "Future Tournament")

    def test_join_full_individual_tournament_fails(self):
        """
        Test that a user cannot join an individual tournament that is already full.
        """
        full_tournament = Tournament.objects.create(
            name="Full Tournament",
            game=self.game,
            start_date=timezone.now() + timedelta(days=1),
            end_date=timezone.now() + timedelta(days=2),
            type="individual",
            max_participants=1,
        )
        # First user joins successfully
        first_user = User.objects.create_user(
            username="firstuser", password="password", phone_number="+555"
        )
        Verification.objects.create(user=first_user, level=2)
        self.client.force_authenticate(user=first_user)
        response = self.client.post(
            f"{self.tournaments_url}tournaments/{full_tournament.id}/join/"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Second user tries to join, which should fail
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f"{self.tournaments_url}tournaments/{full_tournament.id}/join/"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "This tournament is full.")


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

    def _generate_dummy_image(self, name="test.png"):
        file = BytesIO()
        image = Image.new("RGB", (10, 10), "white")
        image.save(file, "png")
        file.name = name
        file.seek(0)
        return SimpleUploadedFile(name, file.read(), content_type="image/png")

    def test_submit_confirm_dispute_flow(self):
        # 1. user1 submits the result
        self.match.status = 'ongoing'
        self.match.save()
        self.client.force_authenticate(user=self.user1)
        data = {
            "winner_id": self.user2.id,
            "result_proof": self._generate_dummy_image(),
        }
        response = self.client.post(
            f"{self.matches_url}{self.match.id}/submit_result/", data, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.match.refresh_from_db()
        self.assertEqual(self.match.status, "pending_confirmation")
        self.assertEqual(self.match.winner_user, self.user2)
        self.assertEqual(self.match.result_submitted_by, self.user1)

        # 2. user2 confirms the result
        self.client.force_authenticate(user=self.user2)
        response = self.client.post(
            f"{self.matches_url}{self.match.id}/confirm_result/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.match.refresh_from_db()
        self.assertEqual(self.match.status, "completed")
        self.assertTrue(self.match.is_confirmed)

        # 3. Reset and test dispute flow
        self.match.status = "pending_confirmation"
        self.match.is_confirmed = False
        self.match.save()

        self.client.force_authenticate(user=self.user2)
        response = self.client.post(
            f"{self.matches_url}{self.match.id}/dispute_result/",
            {"reason": "He cheated!"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.match.refresh_from_db()
        self.assertEqual(self.match.status, "disputed")
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
            Report.objects.filter(
                reporter=self.reporter, reported_user=self.reported
            ).exists()
        )

    def test_create_report_with_in_game_id(self):
        InGameID.objects.create(user=self.reported, game=self.game, player_id="player123")
        self.client.force_authenticate(user=self.reporter)
        data = {
            "reported_player_id": "player123",
            "match": self.match.id,
            "description": "He was rude.",
        }
        response = self.client.post(self.reports_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Report.objects.filter(
                reporter=self.reporter, reported_user=self.reported
            ).exists()
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

    def test_user_cannot_delete_other_report(self):
        """
        Ensures a regular user cannot delete a report they did not create.
        """
        other_reporter = User.objects.create_user(username="other", password="p", phone_number="+304")
        report = Report.objects.create(
            reporter=other_reporter,
            reported_user=self.reported,
            match=self.match,
            description="d",
        )
        self.client.force_authenticate(user=self.reporter)
        response = self.client.delete(f"{self.reports_url}{report.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_delete_other_report(self):
        """
        Ensures an admin can delete any report.
        """
        report = Report.objects.create(
            reporter=self.reporter,
            reported_user=self.reported,
            match=self.match,
            description="d",
        )
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(f"{self.reports_url}{report.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Report.objects.filter(id=report.id).exists())


class GetTournamentWinnersServiceTests(TestCase):
    def setUp(self):
        self.game = Game.objects.create(name="Winners Game")

    def test_team_duel_returns_only_champion(self):
        tournament = Tournament.objects.create(
            name="Duel",
            game=self.game,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=1),
            type="team",
            team_size=5,
        )
        captain_a = User.objects.create_user(
            username="captain_a", password="p", phone_number="+600"
        )
        captain_b = User.objects.create_user(
            username="captain_b", password="p", phone_number="+601"
        )
        team_a = Team.objects.create(name="Alpha", captain=captain_a)
        team_b = Team.objects.create(name="Beta", captain=captain_b)
        tournament.teams.add(team_a, team_b)

        Match.objects.create(
            tournament=tournament,
            match_type="team",
            round=1,
            participant1_team=team_a,
            participant2_team=team_b,
            winner_team=team_a,
            is_confirmed=True,
        )

        winners = list(get_tournament_winners(tournament))

        self.assertEqual(winners, [team_a])

    def test_individual_duel_returns_only_champion(self):
        tournament = Tournament.objects.create(
            name="Solo Duel",
            game=self.game,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=1),
            type="individual",
        )
        player_a = User.objects.create_user(
            username="player_a", password="p", phone_number="+620"
        )
        player_b = User.objects.create_user(
            username="player_b", password="p", phone_number="+621"
        )
        tournament.participants.add(player_a, player_b)

        Match.objects.create(
            tournament=tournament,
            match_type="individual",
            round=1,
            participant1_user=player_a,
            participant2_user=player_b,
            winner_user=player_b,
            is_confirmed=True,
        )
        Match.objects.create(
            tournament=tournament,
            match_type="individual",
            round=2,
            participant1_user=player_a,
            participant2_user=player_b,
            winner_user=player_a,
            is_confirmed=True,
        )
        Match.objects.create(
            tournament=tournament,
            match_type="individual",
            round=3,
            participant1_user=player_a,
            participant2_user=player_b,
            winner_user=player_a,
            is_confirmed=True,
        )

        winners = list(get_tournament_winners(tournament))

        self.assertEqual(winners, [player_a])

    def test_multi_team_tournament_returns_multiple_winners(self):
        tournament = Tournament.objects.create(
            name="League",
            game=self.game,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=1),
            type="team",
            team_size=5,
        )

        teams = []
        for idx in range(4):
            captain = User.objects.create_user(
                username=f"captain_{idx}",
                password="p",
                phone_number=f"+610{idx}",
            )
            team = Team.objects.create(name=f"Team {idx}", captain=captain)
            teams.append(team)

        tournament.teams.add(*teams)

        Match.objects.create(
            tournament=tournament,
            match_type="team",
            round=1,
            participant1_team=teams[0],
            participant2_team=teams[1],
            winner_team=teams[0],
            is_confirmed=True,
        )
        Match.objects.create(
            tournament=tournament,
            match_type="team",
            round=1,
            participant1_team=teams[0],
            participant2_team=teams[2],
            winner_team=teams[0],
            is_confirmed=True,
        )
        Match.objects.create(
            tournament=tournament,
            match_type="team",
            round=1,
            participant1_team=teams[1],
            participant2_team=teams[2],
            winner_team=teams[1],
            is_confirmed=True,
        )
        Match.objects.create(
            tournament=tournament,
            match_type="team",
            round=1,
            participant1_team=teams[3],
            participant2_team=teams[2],
            winner_team=teams[3],
            is_confirmed=True,
        )

        winners = list(get_tournament_winners(tournament))

        self.assertEqual(winners, [teams[0], teams[1], teams[3]])

    def test_multi_individual_tournament_returns_top_five(self):
        tournament = Tournament.objects.create(
            name="Solo League",
            game=self.game,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=1),
            type="individual",
        )

        loser = User.objects.create_user(
            username="loser", password="p", phone_number="+622"
        )
        tournament.participants.add(loser)

        winners = []
        for idx in range(6):
            player = User.objects.create_user(
                username=f"player_{idx}",
                password="p",
                phone_number=f"+623{idx}",
            )
            winners.append(player)
            tournament.participants.add(player)
            Match.objects.create(
                tournament=tournament,
                match_type="individual",
                round=idx + 1,
                participant1_user=player,
                participant2_user=loser,
                winner_user=player,
                is_confirmed=True,
            )

        winners_list = list(get_tournament_winners(tournament))

        expected = sorted(winners, key=lambda user: user.id)[:5]
        self.assertEqual(winners_list, expected)

    def test_custom_winner_slots_limits_output(self):
        tournament = Tournament.objects.create(
            name="Configured Solo League",
            game=self.game,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=1),
            type="individual",
            winner_slots=3,
        )

        anchor = User.objects.create_user(
            username="anchor", password="p", phone_number="+630"
        )
        tournament.participants.add(anchor)

        winners = []
        for idx in range(5):
            player = User.objects.create_user(
                username=f"cfg_player_{idx}",
                password="p",
                phone_number=f"+631{idx}",
            )
            winners.append(player)
            tournament.participants.add(player)
            Match.objects.create(
                tournament=tournament,
                match_type="individual",
                round=idx + 1,
                participant1_user=player,
                participant2_user=anchor,
                winner_user=player,
                is_confirmed=True,
            )

        winners_list = list(get_tournament_winners(tournament))

        expected = sorted(winners, key=lambda user: user.id)[:3]
        self.assertEqual(winners_list, expected)

    def test_duel_respects_champion_only_even_with_custom_slots(self):
        tournament = Tournament.objects.create(
            name="Configured Duel",
            game=self.game,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=1),
            type="team",
            team_size=5,
            winner_slots=4,
        )

        captain_a = User.objects.create_user(
            username="cfg_captain_a", password="p", phone_number="+640"
        )
        captain_b = User.objects.create_user(
            username="cfg_captain_b", password="p", phone_number="+641"
        )
        team_a = Team.objects.create(name="Cfg Alpha", captain=captain_a)
        team_b = Team.objects.create(name="Cfg Beta", captain=captain_b)
        tournament.teams.add(team_a, team_b)

        Match.objects.create(
            tournament=tournament,
            match_type="team",
            round=1,
            participant1_team=team_a,
            participant2_team=team_b,
            winner_team=team_b,
            is_confirmed=True,
        )

        winners = list(get_tournament_winners(tournament))

        self.assertEqual(winners, [team_b])


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

    @patch("tournaments.services.get_tournament_winners")
    def test_create_submission_team_member_allowed(self, mock_get_winners):
        team_tournament = Tournament.objects.create(
            name="Team Tournament",
            game=self.game,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=1),
            is_free=False,
            entry_fee=100,
            type="team",
            team_size=5,
        )
        captain = User.objects.create_user(
            username="captain", password="p", phone_number="+410"
        )
        team = Team.objects.create(name="Winners", captain=captain)
        TeamMembership.objects.create(team=team, user=self.winner)
        mock_get_winners.return_value = [team]

        self.client.force_authenticate(user=self.winner)
        data = {
            "tournament": team_tournament.id,
            "video": self._generate_dummy_image("video.mp4"),
        }
        response = self.client.post(self.submissions_url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            WinnerSubmission.objects.filter(
                winner=self.winner, tournament=team_tournament
            ).exists()
        )

    @patch("tournaments.services.get_tournament_winners")
    def test_create_submission_team_non_member_rejected(self, mock_get_winners):
        outsider = User.objects.create_user(
            username="outsider", password="p", phone_number="+411"
        )
        team_tournament = Tournament.objects.create(
            name="Team Tournament",
            game=self.game,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=1),
            is_free=False,
            entry_fee=100,
            type="team",
            team_size=5,
        )
        captain = User.objects.create_user(
            username="captain2", password="p", phone_number="+412"
        )
        team = Team.objects.create(name="Champions", captain=captain)
        mock_get_winners.return_value = [team]

        self.client.force_authenticate(user=outsider)
        data = {
            "tournament": team_tournament.id,
            "video": self._generate_dummy_image("video.mp4"),
        }
        response = self.client.post(self.submissions_url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            WinnerSubmission.objects.filter(
                winner=outsider, tournament=team_tournament
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

    def test_approve_submission_by_creator(self):
        creator = User.objects.create_user(
            username="creator", password="p", phone_number="+403"
        )
        self.tournament.creator = creator
        self.tournament.save()
        submission = WinnerSubmission.objects.create(
            winner=self.winner, tournament=self.tournament, video="v.mp4"
        )
        self.client.force_authenticate(user=creator)
        response = self.client.post(f"{self.submissions_url}{submission.id}/approve/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        submission.refresh_from_db()
        self.assertEqual(submission.status, "approved")

    def test_reject_submission_by_creator(self):
        creator = User.objects.create_user(
            username="creator", password="p", phone_number="+403"
        )
        self.tournament.creator = creator
        self.tournament.save()
        submission = WinnerSubmission.objects.create(
            winner=self.winner, tournament=self.tournament, video="v.mp4"
        )
        self.client.force_authenticate(user=creator)
        response = self.client.post(f"{self.submissions_url}{submission.id}/reject/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        submission.refresh_from_db()
        self.assertEqual(submission.status, "rejected")

    def test_approve_submission_by_non_creator_fails(self):
        non_creator = User.objects.create_user(
            username="non_creator", password="p", phone_number="+404"
        )
        submission = WinnerSubmission.objects.create(
            winner=self.winner, tournament=self.tournament, video="v.mp4"
        )
        self.client.force_authenticate(user=non_creator)
        response = self.client.post(f"{self.submissions_url}{submission.id}/approve/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_reject_submission_by_non_creator_fails(self):
        non_creator = User.objects.create_user(
            username="non_creator", password="p", phone_number="+404"
        )
        submission = WinnerSubmission.objects.create(
            winner=self.winner, tournament=self.tournament, video="v.mp4"
        )
        self.client.force_authenticate(user=non_creator)
        response = self.client.post(f"{self.submissions_url}{submission.id}/reject/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class GameManagerPermissionsTests(APITestCase):
    def setUp(self):
        self.client = APIClient()


class TournamentImageCRUDTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser(
            username="admin", password="password", phone_number="+501"
        )
        self.client.force_authenticate(user=self.admin_user)
        self.images_url = "/api/tournaments/tournament-images/"

    def _generate_dummy_image(self, name="test.png"):
        file = BytesIO()
        image = Image.new("RGB", (10, 10), "white")
        image.save(file, "png")
        file.name = name
        file.seek(0)
        return SimpleUploadedFile(name, file.read(), content_type="image/png")

    def test_create_tournament_image(self):
        data = {
            "name": "Test Image",
            "image": self._generate_dummy_image(),
        }
        response = self.client.post(self.images_url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(TournamentImage.objects.filter(name="Test Image").exists())

    def test_list_tournament_images(self):
        TournamentImage.objects.create(name="Image 1", image=self._generate_dummy_image("i1.png"))
        TournamentImage.objects.create(name="Image 2", image=self._generate_dummy_image("i2.png"))
        response = self.client.get(self.images_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_update_tournament_image(self):
        image = TournamentImage.objects.create(name="Old Name", image=self._generate_dummy_image())
        data = {"name": "New Name"}
        response = self.client.patch(f"{self.images_url}{image.id}/", data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        image.refresh_from_db()
        self.assertEqual(image.name, "New Name")

    def test_delete_tournament_image(self):
        image = TournamentImage.objects.create(name="To Delete", image=self._generate_dummy_image())
        response = self.client.delete(f"{self.images_url}{image.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(TournamentImage.objects.filter(id=image.id).exists())


class GameManagerPermissionsTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.managed_game = Game.objects.create(name="Managed Game")
        self.other_game = Game.objects.create(name="Other Game")
        self.admin_user = User.objects.create_superuser(
            username="admin", password="password", phone_number="+1"
        )
        self.game_manager = User.objects.create_user(
            username="gamemanager", password="password", phone_number="+2"
        )
        self.regular_user = User.objects.create_user(
            username="regularuser", password="password", phone_number="+3"
        )
        GameManager.objects.create(user=self.game_manager, game=self.managed_game)
        self.tournament_in_managed_game = Tournament.objects.create(
            name="Tournament in Managed Game",
            game=self.managed_game,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=1),
        )
        self.tournaments_url = "/api/tournaments/tournaments/"
        self.tournament_detail_url = (
            f"{self.tournaments_url}{self.tournament_in_managed_game.id}/"
        )

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
        self.assertTrue(
            Tournament.objects.filter(name="New Tournament by Manager").exists()
        )

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


class TournamentFilterTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.game = Game.objects.create(name="Filter Game")
        self.tournaments_url = "/api/tournaments/tournaments/"

        now = timezone.now()
        Tournament.objects.create(
            name="Alpha Tournament",
            game=self.game,
            start_date=now + timedelta(days=10),
            end_date=now + timedelta(days=11),
            entry_fee=10,
        )
        Tournament.objects.create(
            name="Beta Tournament",
            game=self.game,
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=1),
            entry_fee=20,
        )
        Tournament.objects.create(
            name="Gamma Tournament",
            game=self.game,
            start_date=now - timedelta(days=11),
            end_date=now - timedelta(days=10),
            entry_fee=0,
        )

    def test_filter_by_name(self):
        response = self.client.get(self.tournaments_url, {"name": "Alpha"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Alpha Tournament")

    def test_filter_by_status_upcoming(self):
        response = self.client.get(self.tournaments_url, {"status": "upcoming"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Alpha Tournament")

    def test_filter_by_status_ongoing(self):
        response = self.client.get(self.tournaments_url, {"status": "ongoing"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Beta Tournament")

    def test_filter_by_status_finished(self):
        response = self.client.get(self.tournaments_url, {"status": "finished"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Gamma Tournament")

    def test_ordering_by_name_asc(self):
        response = self.client.get(
            self.tournaments_url, {"ordering": "name", "status": "all"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(len(response.data["results"]), 3)
        self.assertEqual(response.data["results"][0]["name"], "Alpha Tournament")
        self.assertEqual(response.data["results"][1]["name"], "Beta Tournament")
        self.assertEqual(response.data["results"][2]["name"], "Gamma Tournament")

    def test_ordering_by_name_desc(self):
        response = self.client.get(
            self.tournaments_url, {"ordering": "-name", "status": "all"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(len(response.data["results"]), 3)
        self.assertEqual(response.data["results"][0]["name"], "Gamma Tournament")
        self.assertEqual(response.data["results"][1]["name"], "Beta Tournament")
        self.assertEqual(response.data["results"][2]["name"], "Alpha Tournament")

    def test_ordering_by_start_date_asc(self):
        response = self.client.get(
            self.tournaments_url, {"ordering": "start_date", "status": "all"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(len(response.data["results"]), 3)
        self.assertEqual(response.data["results"][0]["name"], "Gamma Tournament")
        self.assertEqual(response.data["results"][1]["name"], "Beta Tournament")
        self.assertEqual(response.data["results"][2]["name"], "Alpha Tournament")

    def test_ordering_by_start_date_desc(self):
        response = self.client.get(
            self.tournaments_url, {"ordering": "-start_date", "status": "all"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(len(response.data["results"]), 3)
        self.assertEqual(response.data["results"][0]["name"], "Alpha Tournament")
        self.assertEqual(response.data["results"][1]["name"], "Beta Tournament")
        self.assertEqual(response.data["results"][2]["name"], "Gamma Tournament")

    def test_ordering_by_entry_fee_asc(self):
        response = self.client.get(
            self.tournaments_url, {"ordering": "entry_fee", "status": "all"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(len(response.data["results"]), 3)
        self.assertEqual(response.data["results"][0]["name"], "Gamma Tournament")
        self.assertEqual(response.data["results"][1]["name"], "Alpha Tournament")
        self.assertEqual(response.data["results"][2]["name"], "Beta Tournament")

    def test_ordering_by_entry_fee_desc(self):
        response = self.client.get(
            self.tournaments_url, {"ordering": "-entry_fee", "status": "all"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(len(response.data["results"]), 3)
        self.assertEqual(response.data["results"][0]["name"], "Beta Tournament")
        self.assertEqual(response.data["results"][1]["name"], "Alpha Tournament")
        self.assertEqual(response.data["results"][2]["name"], "Gamma Tournament")


class TournamentColorCRUDTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser(
            username="admin", password="password", phone_number="+601"
        )
        self.client.force_authenticate(user=self.admin_user)
        self.colors_url = "/api/tournaments/tournament-colors/"

    def test_create_tournament_color(self):
        data = {"name": "Red", "rgb_code": "255,0,0"}
        response = self.client.post(self.colors_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(TournamentColor.objects.filter(name="Red").exists())

    def test_list_tournament_colors(self):
        TournamentColor.objects.create(name="Red", rgb_code="255,0,0")
        TournamentColor.objects.create(name="Blue", rgb_code="0,0,255")
        response = self.client.get(self.colors_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_update_tournament_color(self):
        color = TournamentColor.objects.create(name="Old Name", rgb_code="0,0,0")
        data = {"name": "New Name"}
        response = self.client.patch(f"{self.colors_url}{color.id}/", data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        color.refresh_from_db()
        self.assertEqual(color.name, "New Name")

    def test_delete_tournament_color(self):
        color = TournamentColor.objects.create(name="To Delete", rgb_code="0,0,0")
        response = self.client.delete(f"{self.colors_url}{color.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(TournamentColor.objects.filter(id=color.id).exists())

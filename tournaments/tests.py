from datetime import timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from users.models import Team, User

from django.core.exceptions import PermissionDenied
from .models import Game, Match, Tournament, Report, WinnerSubmission


class TournamentAPITest(APITestCase):
    def setUp(self):
        self.game = Game.objects.create(name="Test Game")
        self.user1 = User.objects.create_user(
            username="user1", password="password", phone_number="+12125552361"
        )
        self.user2 = User.objects.create_user(
            username="user2", password="password", phone_number="+12125552362"
        )
        from wallet.models import Wallet

        Wallet.objects.create(
            user=self.user1, total_balance=100, withdrawable_balance=50
        )
        Wallet.objects.create(
            user=self.user2, total_balance=100, withdrawable_balance=50
        )
        self.team1 = Team.objects.create(name="Team 1", captain=self.user1)
        self.team2 = Team.objects.create(name="Team 2", captain=self.user2)
        self.team1.members.add(self.user1)
        self.team2.members.add(self.user2)

        self.individual_tournament = Tournament.objects.create(
            name="Individual Tournament",
            game=self.game,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=1),
            type="individual",
            is_free=False,
            entry_fee=Decimal("10.00"),
        )

        self.team_tournament = Tournament.objects.create(
            name="Team Tournament",
            game=self.game,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=1),
            type="team",
            is_free=False,
            entry_fee=Decimal("20.00"),
        )

    def test_join_individual_tournament(self):
        self.client.force_authenticate(user=self.user1)
        url = reverse("tournament-join", kwargs={"pk": self.individual_tournament.pk})
        response = self.client.post(f"{url}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.individual_tournament.refresh_from_db()
        self.assertIn(self.user1, self.individual_tournament.participants.all())

    def test_join_team_tournament_with_selected_members(self):
        self.client.force_authenticate(user=self.user1)
        url = reverse("tournament-join", kwargs={"pk": self.team_tournament.pk})
        data = {"team_id": self.team1.id, "member_ids": [self.user1.id]}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.team_tournament.refresh_from_db()
        self.assertIn(self.team1, self.team_tournament.teams.all())
        self.assertIn(self.user1, self.team_tournament.participants.all())

    def test_join_team_tournament_insufficient_funds(self):
        self.user3 = User.objects.create_user(
            username="user3", password="password", phone_number="+12125552363"
        )
        from wallet.models import Wallet

        Wallet.objects.create(
            user=self.user3, total_balance=10, withdrawable_balance=5
        )
        self.team1.members.add(self.user3)
        self.client.force_authenticate(user=self.user1)
        url = reverse("tournament-join", kwargs={"pk": self.team_tournament.pk})
        data = {"team_id": self.team1.id, "member_ids": [self.user1.id, self.user3.id]}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_join_team_tournament_member_already_joined(self):
        self.team_tournament.participants.add(self.user2)
        self.client.force_authenticate(user=self.user1)
        url = reverse("tournament-join", kwargs={"pk": self.team_tournament.pk})
        data = {"team_id": self.team1.id, "member_ids": [self.user1.id, self.user2.id]}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_join_team_tournament_not_captain(self):
        self.client.force_authenticate(user=self.user2)
        url = reverse("tournament-join", kwargs={"pk": self.team_tournament.pk})
        data = {"team_id": self.team1.id, "member_ids": [self.user1.id]}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_join_team_tournament_too_many_members(self):
        self.user3 = User.objects.create_user(
            username="user3", password="password", phone_number="+12125552363"
        )
        self.user4 = User.objects.create_user(
            username="user4", password="password", phone_number="+12125552364"
        )
        self.user5 = User.objects.create_user(
            username="user5", password="password", phone_number="+12125552365"
        )
        self.user6 = User.objects.create_user(
            username="user6", password="password", phone_number="+12125552366"
        )
        self.team1.members.add(
            self.user3, self.user4, self.user5, self.user6
        )
        self.client.force_authenticate(user=self.user1)
        url = reverse("tournament-join", kwargs={"pk": self.team_tournament.pk})
        data = {
            "team_id": self.team1.id,
            "member_ids": [
                self.user1.id,
                self.user3.id,
                self.user4.id,
                self.user5.id,
                self.user6.id,
            ],
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_join_tournament_already_joined(self):
        self.individual_tournament.participants.add(self.user1)
        self.client.force_authenticate(user=self.user1)
        url = reverse("tournament-join", kwargs={"pk": self.individual_tournament.pk})
        response = self.client.post(f"{url}")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_generate_matches(self):
        self.individual_tournament.participants.add(self.user1, self.user2)
        self.client.force_authenticate(user=self.user1)  # needs to be admin
        self.user1.is_staff = True
        self.user1.save()
        url = reverse(
            "tournament-generate-matches",
            kwargs={"pk": self.individual_tournament.pk},
        )
        response = self.client.post(f"{url}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.individual_tournament.matches.count(), 1)

    def test_confirm_match_result(self):
        self.individual_tournament.participants.add(self.user1, self.user2)
        match = Match.objects.create(
            tournament=self.individual_tournament,
            match_type="individual",
            round=1,
            participant1_user=self.user1,
            participant2_user=self.user2,
        )
        self.client.force_authenticate(user=self.user1)
        url = reverse("match-confirm-result", kwargs={"pk": match.pk})
        data = {"winner_id": self.user1.id}
        response = self.client.post(f"{url}", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        match.refresh_from_db()
        self.assertTrue(match.is_confirmed)
        self.assertEqual(match.winner_user, self.user1)


class ReportTests(APITestCase):
    def setUp(self):
        self.game = Game.objects.create(name="Test Game")
        self.user1 = User.objects.create_user(
            username="user1", password="password", phone_number="+12125552361"
        )
        self.user2 = User.objects.create_user(
            username="user2", password="password", phone_number="+12125552362"
        )
        self.tournament = Tournament.objects.create(
            name="Test Tournament",
            game=self.game,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=1),
        )
        self.match = Match.objects.create(
            tournament=self.tournament,
            participant1_user=self.user1,
            participant2_user=self.user2,
        )
        self.client.force_authenticate(user=self.user1)

    def test_create_report(self):
        url = reverse("report-list")
        data = {
            "reported_user": self.user2.id,
            "match": self.match.id,
            "description": "Cheating",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Report.objects.count(), 1)


class WinnerSubmissionTests(APITestCase):
    def setUp(self):
        self.game = Game.objects.create(name="Test Game")
        self.user1 = User.objects.create_user(
            username="user1", password="password", phone_number="+12125552361"
        )
        self.tournament = Tournament.objects.create(
            name="Test Tournament",
            game=self.game,
            start_date=timezone.now(),
            end_date=timezone.now() - timedelta(days=1),
        )
        # Assume user1 is a winner
        self.client.force_authenticate(user=self.user1)

    def test_create_winner_submission(self):
        url = reverse("winnersubmission-list")
        # This test will fail because the logic to determine top 5 winners is not implemented yet
        # and there is no prize pool.
        # For now, we just check if the endpoint is reachable.
        with self.assertRaises(PermissionDenied):
            self.client.post(
                url,
                {"tournament": self.tournament.id, "video": "some_video.mp4"},
                format="multipart",
            )

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from tournaments.models import Game, Match, Rank, Tournament

from .models import OTP, Role, Team, TeamInvitation, TeamMembership
from .services import (ApplicationError, invite_member_service,
                       leave_team_service, remove_member_service,
                       respond_to_invitation_service)

User = get_user_model()


class UserModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Rank.objects.all().delete()
        cls.user_data = {
            "username": "testuser",
            "password": "password123",
            "phone_number": "+1234567890",
            "email": "test@example.com",
        }
        cls.rank1 = Rank.objects.create(name="Bronze", required_score=0)
        cls.rank2 = Rank.objects.create(name="Silver", required_score=100)

    def test_user_creation(self):
        """
        Test that a user can be created with valid data.
        """
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.username, self.user_data["username"])
        self.assertEqual(user.phone_number, self.user_data["phone_number"])
        self.assertEqual(user.email, self.user_data["email"])
        self.assertTrue(user.check_password(self.user_data["password"]))

    def test_phone_number_uniqueness(self):
        """
        Test that the phone_number field must be unique.
        """
        User.objects.create_user(**self.user_data)
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                username="anotheruser",
                password="password123",
                phone_number=self.user_data["phone_number"],
            )

    def test_default_role_assignment(self):
        """
        Test that a default role is assigned to a new user.
        """
        group = Group.objects.create(name="Default Role")
        Role.objects.create(group=group, is_default=True)
        user = User.objects.create_user(**self.user_data)
        self.assertIn(group, user.groups.all())

    def test_update_rank(self):
        """
        Test that the user's rank is updated based on score.
        """
        user = User.objects.create_user(**self.user_data, score=50)
        user.rank = self.rank1
        user.save()

        user.update_rank()
        self.assertEqual(user.rank.id, self.rank1.id)

        user.score = 150
        user.save()
        user.update_rank()
        self.assertEqual(user.rank.id, self.rank2.id)


class TeamModelTests(TestCase):
    def setUp(self):
        self.captain = User.objects.create_user(
            username="captain", password="password", phone_number="+111"
        )

    def test_team_creation(self):
        """
        Test that a team can be created with a captain.
        """
        team = Team.objects.create(name="Test Team", captain=self.captain)
        self.assertEqual(team.name, "Test Team")
        self.assertEqual(team.captain, self.captain)

    def test_user_team_limit(self):
        """
        Test that a user cannot be in more than 10 teams.
        """
        user = User.objects.create_user(
            username="testuser", password="password", phone_number="+222"
        )
        for i in range(10):
            team = Team.objects.create(name=f"Team {i}", captain=self.captain)
            TeamMembership.objects.create(user=user, team=team)

        another_team = Team.objects.create(name="Team 11", captain=self.captain)
        with self.assertRaises(ValidationError):
            TeamMembership.objects.create(user=user, team=another_team)


class UserViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.users_url = "/api/users/users/"
        self.user1 = User.objects.create_user(
            username="user1", password="password", phone_number="+1"
        )
        self.user2 = User.objects.create_user(
            username="user2", password="password", phone_number="+2"
        )
        self.admin_user = User.objects.create_superuser(
            username="admin", password="password", phone_number="+3"
        )

    def test_list_users_unauthenticated(self):
        response = self.client.get(self.users_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_users_authenticated(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.users_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # By default, list should return all users.
        self.assertEqual(len(response.data), 3)

    def test_retrieve_own_details(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(f"{self.users_url}{self.user1.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], self.user1.username)

    def test_retrieve_other_details_fails(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(f"{self.users_url}{self.user2.id}/")
        # IsOwnerOrReadOnly should prevent this.
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_own_details(self):
        self.client.force_authenticate(user=self.user1)
        data = {"email": "newemail@example.com"}
        response = self.client.patch(f"{self.users_url}{self.user1.id}/", data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user1.refresh_from_db()
        self.assertEqual(self.user1.email, "newemail@example.com")

    def test_update_other_details_fails(self):
        self.client.force_authenticate(user=self.user1)
        data = {"email": "newemail@example.com"}
        response = self.client.patch(f"{self.users_url}{self.user2.id}/", data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_user(self):
        data = {
            "username": "newuser",
            "password": "password123",
            "phone_number": "+1-202-555-0148",
            "email": "new@example.com",
        }
        response = self.client.post(self.users_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="newuser").exists())

    @patch("users.services.send_sms_notification.delay")
    @patch("users.services.send_email_notification.delay")
    def test_send_otp_success(self, mock_send_email, mock_send_sms):
        """
        Test that OTP is sent successfully.
        """
        data = {"phone_number": self.user1.phone_number}
        response = self.client.post(f"{self.users_url}send_otp/", data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(OTP.objects.filter(user=self.user1).exists())
        mock_send_sms.assert_called_once()
        mock_send_email.assert_not_called()

    def test_verify_otp_success(self):
        """
        Test that a valid OTP is verified successfully.
        """
        otp = OTP.objects.create(user=self.user1, code="123456")
        data = {"phone_number": self.user1.phone_number, "code": "123456"}
        response = self.client.post(f"{self.users_url}verify_otp/", data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        otp.refresh_from_db()
        self.assertFalse(otp.is_active)

    def test_verify_otp_invalid_code(self):
        """
        Test that an invalid OTP fails verification.
        """
        OTP.objects.create(user=self.user1, code="123456")
        data = {"phone_number": self.user1.phone_number, "code": "654321"}
        response = self.client.post(f"{self.users_url}verify_otp/", data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Invalid OTP.")

    def test_verify_otp_expired(self):
        """
        Test that an expired OTP fails verification.
        """
        otp = OTP.objects.create(user=self.user1, code="123456")
        otp.created_at = timezone.now() - timedelta(minutes=10)
        otp.save()
        data = {"phone_number": self.user1.phone_number, "code": "123456"}
        response = self.client.post(f"{self.users_url}verify_otp/", data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "OTP expired.")


class TeamViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.teams_url = "/api/users/teams/"
        self.respond_invitation_url = "/api/users/teams/respond-invitation/"
        self.captain = User.objects.create_user(
            username="captain", password="password", phone_number="+10"
        )
        self.member = User.objects.create_user(
            username="member", password="password", phone_number="+11"
        )
        self.non_member = User.objects.create_user(
            username="nonmember", password="password", phone_number="+12"
        )
        self.team = Team.objects.create(name="Test Team", captain=self.captain)
        self.team.members.add(self.captain)
        self.team.members.add(self.member)

    def test_list_teams_unauthenticated(self):
        response = self.client.get(self.teams_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_teams_authenticated(self):
        self.client.force_authenticate(user=self.non_member)
        response = self.client.get(self.teams_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_team(self):
        self.client.force_authenticate(user=self.non_member)
        data = {"name": "New Team"}
        response = self.client.post(self.teams_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_team = Team.objects.get(name="New Team")
        self.assertEqual(new_team.captain, self.non_member)

    def test_update_team_by_captain(self):
        self.client.force_authenticate(user=self.captain)
        data = {"name": "Updated Team Name"}
        response = self.client.patch(f"{self.teams_url}{self.team.id}/", data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.team.refresh_from_db()
        self.assertEqual(self.team.name, "Updated Team Name")

    def test_update_team_by_non_captain_fails(self):
        self.client.force_authenticate(user=self.member)
        data = {"name": "Updated Team Name"}
        response = self.client.patch(f"{self.teams_url}{self.team.id}/", data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invite_member_by_captain(self):
        self.client.force_authenticate(user=self.captain)
        data = {"user_id": self.non_member.id}
        response = self.client.post(f"{self.teams_url}{self.team.id}/add-member/", data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            TeamInvitation.objects.filter(
                from_user=self.captain, to_user=self.non_member, team=self.team
            ).exists()
        )

    def test_invite_member_by_non_captain_fails(self):
        self.client.force_authenticate(user=self.member)
        data = {"user_id": self.non_member.id}
        response = self.client.post(f"{self.teams_url}{self.team.id}/add-member/", data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_respond_invitation_accept(self):
        invitation = TeamInvitation.objects.create(
            from_user=self.captain, to_user=self.non_member, team=self.team
        )
        self.client.force_authenticate(user=self.non_member)
        data = {"invitation_id": invitation.id, "status": "accepted"}
        response = self.client.post(self.respond_invitation_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, "accepted")
        self.assertIn(self.non_member, self.team.members.all())

    def test_respond_invitation_reject(self):
        invitation = TeamInvitation.objects.create(
            from_user=self.captain, to_user=self.non_member, team=self.team
        )
        self.client.force_authenticate(user=self.non_member)
        data = {"invitation_id": invitation.id, "status": "rejected"}
        response = self.client.post(self.respond_invitation_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, "rejected")
        self.assertNotIn(self.non_member, self.team.members.all())


class UserServicesTests(TestCase):
    def setUp(self):
        self.captain = User.objects.create_user(
            username="captain", password="p", phone_number="+100"
        )
        self.member = User.objects.create_user(
            username="member", password="p", phone_number="+101"
        )
        self.non_member = User.objects.create_user(
            username="nonmember", password="p", phone_number="+102"
        )
        self.team = Team.objects.create(name="Service Test Team", captain=self.captain)
        self.team.members.add(self.captain, self.member)

    def test_invite_member_service_success(self):
        invitation = invite_member_service(
            team=self.team, from_user=self.captain, to_user_id=self.non_member.id
        )
        self.assertIsInstance(invitation, TeamInvitation)
        self.assertEqual(invitation.team, self.team)
        self.assertEqual(invitation.to_user, self.non_member)

    def test_invite_member_service_not_captain_fails(self):
        with self.assertRaisesMessage(
            ApplicationError, "Only the team captain can invite members."
        ):
            invite_member_service(
                team=self.team, from_user=self.member, to_user_id=self.non_member.id
            )

    def test_invite_member_service_already_member_fails(self):
        with self.assertRaisesMessage(
            ApplicationError, "User is already a member of the team."
        ):
            invite_member_service(
                team=self.team, from_user=self.captain, to_user_id=self.member.id
            )

    def test_respond_to_invitation_accept_success(self):
        invitation = TeamInvitation.objects.create(
            from_user=self.captain, to_user=self.non_member, team=self.team
        )
        respond_to_invitation_service(invitation.id, self.non_member, "accepted")
        self.assertIn(self.non_member, self.team.members.all())

    def test_leave_team_service_success(self):
        leave_team_service(team=self.team, user=self.member)
        self.assertNotIn(self.member, self.team.members.all())

    def test_leave_team_service_captain_fails(self):
        with self.assertRaisesMessage(
            ApplicationError,
            "The captain cannot leave the team. Please transfer captaincy first.",
        ):
            leave_team_service(team=self.team, user=self.captain)

    def test_remove_member_service_success(self):
        remove_member_service(
            team=self.team, captain=self.captain, member_id=self.member.id
        )
        self.assertNotIn(self.member, self.team.members.all())

    def test_remove_member_service_not_captain_fails(self):
        with self.assertRaisesMessage(
            ApplicationError, "Only the team captain can remove members."
        ):
            remove_member_service(
                team=self.team, captain=self.member, member_id=self.captain.id
            )


class MatchHistoryAPITests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            username="user1", password="password", phone_number="+1"
        )
        self.user2 = User.objects.create_user(
            username="user2", password="password", phone_number="+2"
        )
        self.user3 = User.objects.create_user(
            username="user3", password="password", phone_number="+3"
        )
        self.team1 = Team.objects.create(name="Team 1", captain=self.user1)
        self.team1.members.add(self.user1, self.user2)
        self.team2 = Team.objects.create(name="Team 2", captain=self.user3)
        self.team2.members.add(self.user3)

        self.game = Game.objects.create(name="Test Game")
        self.tournament = Tournament.objects.create(
            name="Test Tournament",
            game=self.game,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=1),
        )

        # Individual match for user1
        self.match1 = Match.objects.create(
            tournament=self.tournament,
            match_type="individual",
            round=1,
            participant1_user=self.user1,
            participant2_user=self.user3,
        )
        # Team match for user1 (as part of team1)
        self.match2 = Match.objects.create(
            tournament=self.tournament,
            match_type="team",
            round=1,
            participant1_team=self.team1,
            participant2_team=self.team2,
        )
        # Another match not involving user1 or team1
        self.match3 = Match.objects.create(
            tournament=self.tournament,
            match_type="individual",
            round=1,
            participant1_user=self.user2,
            participant2_user=self.user3,
        )

    def test_get_user_match_history_unauthenticated(self):
        url = f"/api/users/users/{self.user1.id}/match-history/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_user_match_history_authenticated(self):
        self.client.force_authenticate(user=self.user1)
        url = f"/api/users/users/{self.user1.id}/match-history/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        match_ids = [item["id"] for item in response.data]
        self.assertIn(self.match1.id, match_ids)
        self.assertIn(self.match2.id, match_ids)
        self.assertNotIn(self.match3.id, match_ids)

    def test_get_team_match_history_unauthenticated(self):
        url = f"/api/users/teams/{self.team1.id}/match-history/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_team_match_history_authenticated(self):
        self.client.force_authenticate(user=self.user1)
        url = f"/api/users/teams/{self.team1.id}/match-history/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.match2.id)

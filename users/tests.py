from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Team, TeamInvitation, OTP, Role, TeamMembership
from django.contrib.auth.models import Group
from django.db.utils import IntegrityError
from tournaments.models import Rank

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


from django.core.exceptions import ValidationError

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

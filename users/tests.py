from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from tournaments.models import Game

from .models import InGameID, Team, User, TeamInvitation, OTP


class UserTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.game = Game.objects.create(
            name="Test Game", description="Test Description"
        )
        self.user_data = {
            "username": "testuser",
            "password": "testpassword",
            "email": "test@example.com",
            "phone_number": "+12125552368",
        }

    def test_create_user(self):
        url = reverse("user-list")
        response = self.client.post(f"{url}", self.user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().username, "testuser")

    def test_create_user_with_in_game_id(self):
        url = reverse("user-list")
        data = {
            **self.user_data,
            "in_game_ids": [{"game": self.game.id, "player_id": "testplayer"}],
        }
        response = self.client.post(f"{url}", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(InGameID.objects.count(), 1)
        self.assertEqual(InGameID.objects.get().player_id, "testplayer")

    def test_create_user_with_existing_username(self):
        User.objects.create_user(**self.user_data)
        url = reverse("user-list")
        response = self.client.post(f"{url}", self.user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_user_with_existing_email(self):
        User.objects.create_user(**self.user_data)
        self.user_data["username"] = "newuser"
        self.user_data["phone_number"] = "+12125552369"
        url = reverse("user-list")
        response = self.client.post(f"{url}", self.user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_user_with_existing__phone_number(self):
        User.objects.create_user(**self.user_data)
        self.user_data["username"] = "newuser"
        self.user_data["email"] = "new@example.com"
        url = reverse("user-list")
        response = self.client.post(f"{url}", self.user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TeamTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            username="user1", password="testpassword", phone_number="+12125552368"
        )
        self.user2 = User.objects.create_user(
            username="user2", password="testpassword", phone_number="+12125552369"
        )
        self.client.force_authenticate(user=self.user1)
        self.team_data = {
            "name": "Test Team",
            "captain": self.user1.id,
            "members": [self.user1.id, self.user2.id],
        }

    def test_create_team(self):
        url = reverse("team-list")
        response = self.client.post(f"{url}", self.team_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Team.objects.count(), 1)
        self.assertEqual(Team.objects.get().name, "Test Team")

    def test_create_team_with_existing_name(self):
        Team.objects.create(name="Test Team", captain=self.user1)
        url = reverse("team-list")
        response = self.client.post(f"{url}", self.team_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_member_to_team(self):
        team = Team.objects.create(name="Test Team", captain=self.user1)
        team.members.add(self.user1)
        url = reverse("team-add-member", kwargs={"pk": team.pk})
        data = {"user_id": self.user2.id}
        response = self.client.post(f"{url}", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(team.members.count(), 2)

    def test_add_existing_member_to_team(self):
        team = Team.objects.create(name="Test Team", captain=self.user1)
        team.members.add(self.user2)
        url = reverse("team-add-member", kwargs={"pk": team.pk})
        data = {"user_id": self.user2.id}
        response = self.client.post(f"{url}", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_non_existent_user_to_team(self):
        team = Team.objects.create(name="Test Team", captain=self.user1)
        url = reverse("team-add-member", kwargs={"pk": team.pk})
        data = {"user_id": 999}
        response = self.client.post(f"{url}", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_remove_member_from_team(self):
        team = Team.objects.create(name="Test Team", captain=self.user1)
        team.members.add(self.user1)
        team.members.add(self.user2)
        url = reverse("team-remove-member", kwargs={"pk": team.pk})
        data = {"user_id": self.user2.id}
        response = self.client.post(f"{url}", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(team.members.count(), 1)

    def test_remove_non_existent_member_from_team(self):
        team = Team.objects.create(name="Test Team", captain=self.user1)
        url = reverse("team-remove-member", kwargs={"pk": team.pk})
        data = {"user_id": self.user2.id}
        response = self.client.post(f"{url}", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_captain_cannot_add_member(self):
        self.client.force_authenticate(user=self.user2)
        team = Team.objects.create(name="Test Team", captain=self.user1)
        url = reverse("team-add-member", kwargs={"pk": team.pk})
        data = {"user_id": self.user2.id}
        response = self.client.post(f"{url}", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class InvitationTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            username="user1", password="testpassword", phone_number="+12125552368"
        )
        self.user2 = User.objects.create_user(
            username="user2", password="testpassword", phone_number="+12125552369"
        )
        self.team = Team.objects.create(name="Test Team", captain=self.user1)
        self.client.force_authenticate(user=self.user1)

    def test_invite_member(self):
        url = reverse("team-invite-member", kwargs={"pk": self.team.pk})
        data = {"user_id": self.user2.id}
        response = self.client.post(f"{url}", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(TeamInvitation.objects.count(), 1)

    def test_respond_invitation_accepted(self):
        invitation = TeamInvitation.objects.create(
            from_user=self.user1, to_user=self.user2, team=self.team
        )
        self.client.force_authenticate(user=self.user2)
        url = reverse("team-respond-invitation")
        data = {"invitation_id": invitation.id, "status": "accepted"}
        response = self.client.post(f"{url}", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.team.refresh_from_db()
        self.assertIn(self.user2, self.team.members.all())

    def test_respond_invitation_rejected(self):
        invitation = TeamInvitation.objects.create(
            from_user=self.user1, to_user=self.user2, team=self.team
        )
        self.client.force_authenticate(user=self.user2)
        url = reverse("team-respond-invitation")
        data = {"invitation_id": invitation.id, "status": "rejected"}
        response = self.client.post(f"{url}", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.team.refresh_from_db()
        self.assertNotIn(self.user2, self.team.members.all())


class DashboardTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="user1", password="testpassword", phone_number="+12125552368"
        )
        self.client.force_authenticate(user=self.user)

    def test_get_dashboard(self):
        url = reverse("dashboard")
        response = self.client.get(f"{url}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class OTPTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="user1",
            password="testpassword",
            phone_number="+12125552368",
            email="test@example.com",
        )

    def test_send_otp(self):
        url = reverse("user-send-otp")
        data = {"phone_number": "+12125552368"}
        response = self.client.post(f"{url}", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(OTP.objects.count(), 1)

    def test_verify_otp(self):
        otp = OTP.objects.create(user=self.user, code="123456")
        url = reverse("user-verify-otp")
        data = {"phone_number": "+12125552368", "code": "123456"}
        response = self.client.post(f"{url}", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_non_captain_cannot_remove_member(self):
        self.client.force_authenticate(user=self.user2)
        team = Team.objects.create(name="Test Team", captain=self.user1)
        team.members.add(self.user2)
        url = reverse("team-remove-member", kwargs={"pk": team.pk})
        data = {"user_id": self.user2.id}
        response = self.client.post(f"{url}", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

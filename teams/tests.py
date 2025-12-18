from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from users.models import User

from .models import Team, TeamInvitation


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


class TeamViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.teams_url = reverse("team-list")
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
        self.assertEqual(response.status_code, status.HTTP_200_OK)

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

    def test_invitations_include_team_details(self):
        invitation = TeamInvitation.objects.create(
            from_user=self.captain, to_user=self.non_member, team=self.team
        )
        self.client.force_authenticate(user=self.non_member)

        response = self.client.get(reverse("team-invitations"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        invitation_data = response.data[0]

        self.assertEqual(invitation_data["id"], invitation.id)
        self.assertEqual(invitation_data["team"]["id"], self.team.id)
        self.assertEqual(invitation_data["team"]["name"], self.team.name)
        self.assertEqual(invitation_data["team"]["captain"], self.captain.id)

        member_ids = {member["id"] for member in invitation_data["team"]["members"]}
        self.assertIn(self.captain.id, member_ids)
        self.assertIn(self.member.id, member_ids)

from django.urls import reverse
from rest_framework import status
from django.test import TestCase
from rest_framework.test import APIClient
from .models import User, Team, InGameID
from tournaments.models import Game

class UserTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.game = Game.objects.create(name='Test Game', description='Test Description')
        self.user_data = {
            'username': 'testuser',
            'password': 'testpassword',
            'email': 'test@example.com',
            'phone_number': '+12125552368',
        }

    def test_create_user(self):
        url = reverse('user-list')
        response = self.client.post(f'{url}', self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().username, 'testuser')

    def test_create_user_with_in_game_id(self):
        url = reverse('user-list')
        data = {
            **self.user_data,
            'in_game_ids': [
                {
                    'game': self.game.id,
                    'player_id': 'testplayer'
                }
            ]
        }
        response = self.client.post(f'{url}', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(InGameID.objects.count(), 1)
        self.assertEqual(InGameID.objects.get().player_id, 'testplayer')

    def test_create_user_with_existing_username(self):
        User.objects.create_user(**self.user_data)
        url = reverse('user-list')
        response = self.client.post(f'{url}', self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_user_with_existing_email(self):
        User.objects.create_user(**self.user_data)
        self.user_data['username'] = 'newuser'
        self.user_data['phone_number'] = '+12125552369'
        url = reverse('user-list')
        response = self.client.post(f'{url}', self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_user_with_existing__phone_number(self):
        User.objects.create_user(**self.user_data)
        self.user_data['username'] = 'newuser'
        self.user_data['email'] = 'new@example.com'
        url = reverse('user-list')
        response = self.client.post(f'{url}', self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TeamTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(username='user1', password='testpassword', phone_number='+12125552368')
        self.user2 = User.objects.create_user(username='user2', password='testpassword', phone_number='+12125552369')
        self.client.force_authenticate(user=self.user1)
        self.team_data = {
            'name': 'Test Team',
            'captain': self.user1.id,
            'members': [self.user1.id, self.user2.id]
        }

    def test_create_team(self):
        url = reverse('team-list')
        response = self.client.post(f'{url}', self.team_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Team.objects.count(), 1)
        self.assertEqual(Team.objects.get().name, 'Test Team')

    def test_create_team_with_existing_name(self):
        Team.objects.create(name='Test Team', captain=self.user1)
        url = reverse('team-list')
        response = self.client.post(f'{url}', self.team_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_member_to_team(self):
        team = Team.objects.create(name='Test Team', captain=self.user1)
        url = reverse('team-add-member', kwargs={'pk': team.pk})
        data = {'user_id': self.user2.id}
        response = self.client.post(f'{url}', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(team.members.count(), 1)

    def test_add_existing_member_to_team(self):
        team = Team.objects.create(name='Test Team', captain=self.user1)
        team.members.add(self.user2)
        url = reverse('team-add-member', kwargs={'pk': team.pk})
        data = {'user_id': self.user2.id}
        response = self.client.post(f'{url}', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_non_existent_user_to_team(self):
        team = Team.objects.create(name='Test Team', captain=self.user1)
        url = reverse('team-add-member', kwargs={'pk': team.pk})
        data = {'user_id': 999}
        response = self.client.post(f'{url}', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_remove_member_from_team(self):
        team = Team.objects.create(name='Test Team', captain=self.user1)
        team.members.add(self.user2)
        url = reverse('team-remove-member', kwargs={'pk': team.pk})
        data = {'user_id': self.user2.id}
        response = self.client.post(f'{url}', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(team.members.count(), 0)

    def test_remove_non_existent_member_from_team(self):
        team = Team.objects.create(name='Test Team', captain=self.user1)
        url = reverse('team-remove-member', kwargs={'pk': team.pk})
        data = {'user_id': self.user2.id}
        response = self.client.post(f'{url}', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_captain_cannot_add_member(self):
        self.client.force_authenticate(user=self.user2)
        team = Team.objects.create(name='Test Team', captain=self.user1)
        url = reverse('team-add-member', kwargs={'pk': team.pk})
        data = {'user_id': self.user2.id}
        response = self.client.post(f'{url}', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_captain_cannot_remove_member(self):
        self.client.force_authenticate(user=self.user2)
        team = Team.objects.create(name='Test Team', captain=self.user1)
        team.members.add(self.user2)
        url = reverse('team-remove-member', kwargs={'pk': team.pk})
        data = {'user_id': self.user2.id}
        response = self.client.post(f'{url}', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

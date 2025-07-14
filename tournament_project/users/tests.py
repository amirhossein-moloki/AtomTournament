from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import User, Team
from tournaments.models import Game

class UserRegistrationTest(APITestCase):
    def test_registration(self):
        url = reverse('user-register')
        data = {
            'username': 'testuser',
            'password': 'testpassword',
            'email': 'test@example.com',
            'phone_number': '+12125552368',
            'in_game_ids': []
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().username, 'testuser')

class TeamCreationTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword', phone_number='+12125552368')
        self.client.force_authenticate(user=self.user)

    def test_create_team(self):
        url = reverse('team-list')
        data = {
            'name': 'Test Team',
            'members': [self.user.id]
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Team.objects.count(), 1)
        self.assertEqual(Team.objects.get().name, 'Test Team')
        self.assertEqual(Team.objects.get().captain, self.user)

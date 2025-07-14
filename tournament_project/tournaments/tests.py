from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Game, Tournament, Match
from users.models import User
import datetime

class GameTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_authenticate(user=self.user)

    def test_create_game(self):
        url = reverse('game-list')
        data = {'name': 'New Game', 'description': 'A new game'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

class TournamentTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_authenticate(user=self.user)
        self.game = Game.objects.create(name='Test Game')
        self.start_date = datetime.datetime.now() + datetime.timedelta(days=1)
        self.end_date = self.start_date + datetime.timedelta(days=2)

    def test_create_tournament(self):
        url = reverse('tournament-list')
        data = {
            'name': 'Test Tournament',
            'game': self.game.id,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

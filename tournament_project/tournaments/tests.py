from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Game, Tournament
from users.models import User
import datetime

class TournamentCreationTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_authenticate(user=self.user)
        self.game = Game.objects.create(name='Test Game', description='A test game')

    def test_create_tournament(self):
        url = reverse('tournament-list')
        data = {
            'name': 'Test Tournament',
            'game': self.game.id,
            'start_date': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'end_date': (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)).isoformat(),
            'type': 'individual'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Tournament.objects.count(), 1)
        self.assertEqual(Tournament.objects.get().name, 'Test Tournament')

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import User

class UserRegistrationTest(APITestCase):
    def test_registration(self):
        url = reverse('user-list') + 'register/'
        data = {
            'username': 'testuser',
            'password': 'testpassword',
            'email': 'test@example.com',
            'phone_number': '+12125552368',
            'profile': {
                'in_game_ids': []
            }
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().username, 'testuser')

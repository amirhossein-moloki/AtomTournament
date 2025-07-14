from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import User, Team

class UserTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_authenticate(user=self.user)

    def test_create_user(self):
        url = reverse('user-list')
        data = {'username': 'newuser', 'password': 'newpassword'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_get_user(self):
        url = reverse('user-detail', args=[self.user.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

class TeamTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_authenticate(user=self.user)
        self.team = Team.objects.create(name='Test Team', captain=self.user)

    def test_create_team(self):
        url = reverse('team-list')
        data = {'name': 'New Team', 'captain': self.user.id, 'members': [self.user.id]}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_get_team(self):
        url = reverse('team-detail', args=[self.team.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

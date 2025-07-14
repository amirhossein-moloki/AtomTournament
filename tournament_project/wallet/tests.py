from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Wallet, Transaction
from users.models import User

class WalletTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_authenticate(user=self.user)
        self.wallet = Wallet.objects.create(user=self.user, total_balance=100, withdrawable_balance=50)

    def test_get_wallet(self):
        url = reverse('wallet-detail', args=[self.wallet.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

class TransactionTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_authenticate(user=self.user)
        self.wallet = Wallet.objects.create(user=self.user)

    def test_create_transaction(self):
        url = reverse('transaction-list')
        data = {'wallet': self.wallet.id, 'amount': 10, 'transaction_type': 'deposit'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

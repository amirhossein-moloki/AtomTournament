from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Wallet
from users.models import User
from .services import WalletService

class WalletServiceTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_authenticate(user=self.user)

    def test_deposit(self):
        WalletService.deposit(self.user, 100)
        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(wallet.total_balance, 100)
        self.assertEqual(wallet.withdrawable_balance, 100)

    def test_withdraw(self):
        WalletService.deposit(self.user, 100)
        WalletService.withdraw(self.user, 50)
        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(wallet.total_balance, 50)
        self.assertEqual(wallet.withdrawable_balance, 50)

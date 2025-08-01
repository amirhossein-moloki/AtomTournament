from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from .models import Wallet, Transaction
from tournament_project.celery import app as celery_app

User = get_user_model()

class WalletModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password', phone_number='+1234567890')
        self.old_eager = celery_app.conf.task_always_eager
        celery_app.conf.task_always_eager = True

    def tearDown(self):
        celery_app.conf.task_always_eager = self.old_eager

    def test_wallet_creation_signal(self):
        # A wallet should be created automatically for a new user.
        # This test will likely fail until we find or create the signal handler.
        self.assertTrue(hasattr(self.user, 'wallet'))
        self.assertIsInstance(self.user.wallet, Wallet)


class TransactionModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password', phone_number='+1234567890')
        # Assuming a wallet is created for the user.
        if not hasattr(self.user, 'wallet'):
            Wallet.objects.create(user=self.user)
        self.wallet = self.user.wallet
        self.old_eager = celery_app.conf.task_always_eager
        celery_app.conf.task_always_eager = True

    def tearDown(self):
        celery_app.conf.task_always_eager = self.old_eager

    def test_deposit_updates_balance(self):
        # This test will fail until the balance update logic is implemented.
        initial_balance = self.wallet.total_balance
        transaction = Transaction.objects.create(wallet=self.wallet, amount=100, transaction_type='deposit')
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.total_balance, initial_balance + 100)


class WalletViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='password', phone_number='+1234567890')
        self.client.force_authenticate(user=self.user)
        if not hasattr(self.user, 'wallet'):
            Wallet.objects.create(user=self.user)
        self.old_eager = celery_app.conf.task_always_eager
        celery_app.conf.task_always_eager = True

    def tearDown(self):
        celery_app.conf.task_always_eager = self.old_eager

    def test_get_wallet_details(self):
        # TODO: Write test
        pass

from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Wallet
from .services import update_wallet_balance
from decimal import Decimal

User = get_user_model()

class WalletServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")
        self.wallet = Wallet.objects.create(user=self.user, total_balance=100, withdrawable_balance=50)

    def test_deposit(self):
        """
        Tests the deposit functionality.
        """
        update_wallet_balance(self.user, Decimal('50.00'), 'deposit')
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.total_balance, Decimal('150.00'))

    def test_withdrawal(self):
        """
        Tests the withdrawal functionality.
        """
        update_wallet_balance(self.user, Decimal('30.00'), 'withdrawal')
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.withdrawable_balance, Decimal('20.00'))
        self.assertEqual(self.wallet.total_balance, Decimal('70.00'))

    def test_insufficient_withdrawable_balance(self):
        """
        Tests withdrawal with insufficient withdrawable balance.
        """
        with self.assertRaises(ValueError):
            update_wallet_balance(self.user, Decimal('60.00'), 'withdrawal')

    def test_entry_fee(self):
        """
        Tests paying an entry fee.
        """
        update_wallet_balance(self.user, Decimal('20.00'), 'entry_fee')
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.total_balance, Decimal('80.00'))

    def test_insufficient_total_balance_for_entry_fee(self):
        """
        Tests paying an entry fee with insufficient total balance.
        """
        with self.assertRaises(ValueError):
            update_wallet_balance(self.user, Decimal('110.00'), 'entry_fee')

    def test_prize(self):
        """
        Tests receiving a prize.
        """
        update_wallet_balance(self.user, Decimal('100.00'), 'prize')
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.total_balance, Decimal('200.00'))
        self.assertEqual(self.wallet.withdrawable_balance, Decimal('150.00'))

from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient, APITestCase
from rest_framework import status

from .models import Transaction, Wallet

User = get_user_model()


class WalletSignalTests(TestCase):
    """Tests for wallet signal handlers."""

    def test_wallet_is_created_for_new_user(self):
        """
        Test that a Wallet instance is automatically created
        when a new User is created.
        """
        user = User.objects.create_user(
            username="newuser", password="password", phone_number="+9876543210"
        )
        self.assertTrue(hasattr(user, "wallet"))
        self.assertIsInstance(user.wallet, Wallet)
        self.assertEqual(Wallet.objects.count(), 1)
        self.assertEqual(user.wallet.total_balance, 0)


@patch("wallet.signals.send_email_notification.delay")
@patch("wallet.signals.send_sms_notification.delay")
class TransactionSignalTests(TestCase):
    """Tests for transaction signal handlers."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="password",
            phone_number="+1234567890",
            email="test@example.com",
        )
        self.wallet = self.user.wallet
        self.wallet.total_balance = Decimal("100.00")
        self.wallet.withdrawable_balance = Decimal("80.00")
        self.wallet.save()

    def test_deposit_updates_balance_correctly(
        self, mock_send_sms, mock_send_email
    ):
        """Test that a 'deposit' transaction correctly updates wallet balances."""
        Transaction.objects.create(
            wallet=self.wallet, amount=Decimal("50.00"), transaction_type="deposit"
        )
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.total_balance, Decimal("150.00"))
        self.assertEqual(self.wallet.withdrawable_balance, Decimal("130.00"))
        mock_send_sms.assert_called_once()
        mock_send_email.assert_called_once()

    def test_prize_updates_balance_correctly(self, mock_send_sms, mock_send_email):
        """Test that a 'prize' transaction correctly updates wallet balances."""
        Transaction.objects.create(
            wallet=self.wallet, amount=Decimal("200.00"), transaction_type="prize"
        )
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.total_balance, Decimal("300.00"))
        self.assertEqual(self.wallet.withdrawable_balance, Decimal("280.00"))
        mock_send_sms.assert_called_once()
        mock_send_email.assert_called_once()

    def test_entry_fee_updates_balance_correctly(
        self, mock_send_sms, mock_send_email
    ):
        """Test that an 'entry_fee' transaction correctly updates wallet balances."""
        Transaction.objects.create(
            wallet=self.wallet, amount=Decimal("10.00"), transaction_type="entry_fee"
        )
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.total_balance, Decimal("90.00"))
        self.assertEqual(self.wallet.withdrawable_balance, Decimal("70.00"))
        mock_send_sms.assert_called_once()
        mock_send_email.assert_called_once()

    def test_withdrawal_updates_balance_correctly(
        self, mock_send_sms, mock_send_email
    ):
        """Test that a 'withdrawal' transaction correctly updates wallet balances."""
        Transaction.objects.create(
            wallet=self.wallet, amount=Decimal("30.00"), transaction_type="withdrawal"
        )
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.total_balance, Decimal("70.00"))
        self.assertEqual(self.wallet.withdrawable_balance, Decimal("50.00"))
        mock_send_sms.assert_called_once()
        mock_send_email.assert_called_once()

    def test_multiple_transactions_are_handled_correctly(
        self, mock_send_sms, mock_send_email
    ):
        """Test a sequence of transactions to ensure the final balance is correct."""
        # 1. Deposit 100
        Transaction.objects.create(
            wallet=self.wallet, amount=Decimal("100.00"), transaction_type="deposit"
        )
        # 2. Pay entry fee of 25
        Transaction.objects.create(
            wallet=self.wallet, amount=Decimal("25.00"), transaction_type="entry_fee"
        )
        # 3. Win prize of 50
        Transaction.objects.create(
            wallet=self.wallet, amount=Decimal("50.00"), transaction_type="prize"
        )
        # 4. Withdraw 120
        Transaction.objects.create(
            wallet=self.wallet, amount=Decimal("120.00"), transaction_type="withdrawal"
        )

        self.wallet.refresh_from_db()
        # Initial: Total 100, Withdrawable 80
        # 1. Deposit 100 -> Total 200, Withdrawable 180
        # 2. Fee 25 -> Total 175, Withdrawable 155
        # 3. Prize 50 -> Total 225, Withdrawable 205
        # 4. Withdraw 120 -> Total 105, Withdrawable 85
        self.assertEqual(self.wallet.total_balance, Decimal("105.00"))
        self.assertEqual(self.wallet.withdrawable_balance, Decimal("85.00"))
        self.assertEqual(mock_send_sms.call_count, 4)
        self.assertEqual(mock_send_email.call_count, 4)


class WalletViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="password", phone_number="+1112223333"
        )
        self.client.force_authenticate(user=self.user)
        self.wallet = self.user.wallet
        # The URL might need to be adjusted based on the root URLconf
        self.wallet_url = f"/api/wallet/wallets/{self.wallet.id}/"

    def test_get_wallet_details_unauthorized(self):
        """Test that unauthenticated users cannot access wallet details."""
        self.client.logout()
        response = self.client.get(self.wallet_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_own_wallet_details(self):
        """Test that a user can retrieve their own wallet details."""
        response = self.client.get(self.wallet_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.wallet.id)
        self.assertEqual(Decimal(response.data["total_balance"]), self.wallet.total_balance)

    def test_cannot_get_other_user_wallet_details(self):
        """Test that a user cannot retrieve another user's wallet details."""
        other_user = User.objects.create_user(
            username="otheruser", password="password", phone_number="+4445556666"
        )
        other_wallet_url = f"/api/wallet/wallets/{other_user.wallet.id}/"
        response = self.client.get(other_wallet_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

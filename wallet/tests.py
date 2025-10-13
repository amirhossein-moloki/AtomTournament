import json
from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .models import Transaction, Wallet
from .serializers import PaymentSerializer
from .services import ZibalService

User = get_user_model()


class PaymentSerializerTests(SimpleTestCase):
    def test_amount_with_ten_digits_is_valid(self):
        serializer = PaymentSerializer(data={"amount": "1234567890"})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_amount_with_decimal_digits_within_limit_is_valid(self):
        serializer = PaymentSerializer(data={"amount": "12345.67"})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_amount_exceeding_digit_limit_returns_error(self):
        serializer = PaymentSerializer(data={"amount": "12345678901"})
        self.assertFalse(serializer.is_valid())
        self.assertIn(
            "Ensure that there are no more than 10 digits in total.",
            serializer.errors["amount"],
        )


class ZibalServiceTests(SimpleTestCase):
    @patch("wallet.services.requests.post")
    def test_create_payment_successful(self, mock_post):
        mock_response = Mock()
        expected_response = {"result": 100, "trackId": 12345}
        mock_response.json.return_value = expected_response
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        service = ZibalService()
        result = service.create_payment(
            amount=10000,
            description="Test payment",
            callback_url="https://example.com/callback",
            order_id="test-order-id",
            mobile="09123456789",
        )

        self.assertEqual(result, expected_response)
        mock_post.assert_called_once()
        self.assertIn("request", mock_post.call_args[0][0])

    @patch("wallet.services.requests.post")
    def test_verify_payment_successful(self, mock_post):
        mock_response = Mock()
        expected_response = {"result": 100, "status": 1}
        mock_response.json.return_value = expected_response
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        service = ZibalService()
        result = service.verify_payment(track_id=12345)

        self.assertEqual(result, expected_response)
        mock_post.assert_called_once()
        self.assertIn("verify", mock_post.call_args[0][0])

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


from .services import process_transaction


class WalletServiceTests(TestCase):
    """Tests for the wallet service layer."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="password",
            phone_number="+1234567890",
            email="test@example.com",
        )
        self.wallet = self.user.wallet
        self.wallet.total_balance = Decimal("2000000.00")
        self.wallet.withdrawable_balance = Decimal("2000000.00")
        self.wallet.save()

    def test_withdrawal_fails_if_amount_is_less_than_minimum(self):
        """Test that a withdrawal fails if the amount is less than the minimum."""
        _, error = process_transaction(
            user=self.user,
            amount=Decimal("500000.00"),
            transaction_type="withdrawal",
        )
        self.assertIsNotNone(error)
        self.assertIn("Minimum withdrawal amount", error)

    def test_withdrawal_fails_if_within_24_hours_of_last_withdrawal(self):
        """Test that a withdrawal fails if another one was made within 24 hours."""
        # First successful withdrawal
        process_transaction(
            user=self.user,
            amount=Decimal("1000000.00"),
            transaction_type="withdrawal",
        )

        # Second attempt within 24 hours
        _, error = process_transaction(
            user=self.user,
            amount=Decimal("1000000.00"),
            transaction_type="withdrawal",
        )
        self.assertIsNotNone(error)
        self.assertIn("one withdrawal every 24 hours", error)

    def test_deposit_updates_balance_correctly(self):
        """Test that a 'deposit' transaction correctly updates wallet balances."""
        transaction, error = process_transaction(
            user=self.user, amount=Decimal("500000.00"), transaction_type="deposit"
        )
        self.assertIsNone(error)
        self.assertIsNotNone(transaction)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.total_balance, Decimal("2500000.00"))
        self.assertEqual(self.wallet.withdrawable_balance, Decimal("2500000.00"))

    def test_prize_updates_balance_correctly(self):
        """Test that a 'prize' transaction correctly updates wallet balances."""
        transaction, error = process_transaction(
            user=self.user, amount=Decimal("200000.00"), transaction_type="prize"
        )
        self.assertIsNone(error)
        self.assertIsNotNone(transaction)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.total_balance, Decimal("2200000.00"))
        self.assertEqual(self.wallet.withdrawable_balance, Decimal("2200000.00"))

    def test_entry_fee_updates_balance_correctly(self):
        """Test that an 'entry_fee' transaction correctly updates wallet balances."""
        transaction, error = process_transaction(
            user=self.user, amount=Decimal("100000.00"), transaction_type="entry_fee"
        )
        self.assertIsNone(error)
        self.assertIsNotNone(transaction)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.total_balance, Decimal("1900000.00"))
        self.assertEqual(self.wallet.withdrawable_balance, Decimal("1900000.00"))

    def test_withdrawal_updates_balance_correctly(self):
        """Test that a 'withdrawal' transaction correctly updates wallet balances."""
        transaction, error = process_transaction(
            user=self.user,
            amount=Decimal("1000000.00"),
            transaction_type="withdrawal",
        )
        self.assertIsNone(error)
        self.assertIsNotNone(transaction)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.total_balance, Decimal("1000000.00"))
        self.assertEqual(self.wallet.withdrawable_balance, Decimal("1000000.00"))

    def test_withdrawal_insufficient_funds(self):
        """Test that a withdrawal fails if funds are insufficient."""
        transaction, error = process_transaction(
            user=self.user,
            amount=Decimal("3000000.00"),
            transaction_type="withdrawal",
        )
        self.assertIsNone(transaction)
        self.assertIsNotNone(error)
        self.assertIn("Insufficient withdrawable balance", error)
        # Check that the balance has not changed
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.total_balance, Decimal("2000000.00"))

    def test_multiple_transactions_are_handled_correctly(self):
        """Test a sequence of transactions to ensure the final balance is correct."""
        # 1. Deposit 1000000
        process_transaction(
            user=self.user, amount=Decimal("1000000.00"), transaction_type="deposit"
        )
        # 2. Pay entry fee of 250000
        process_transaction(
            user=self.user, amount=Decimal("250000.00"), transaction_type="entry_fee"
        )
        # 3. Win prize of 500000
        process_transaction(
            user=self.user, amount=Decimal("500000.00"), transaction_type="prize"
        )
        # 4. Withdraw 1200000
        process_transaction(
            user=self.user,
            amount=Decimal("1200000.00"),
            transaction_type="withdrawal",
        )

        self.wallet.refresh_from_db()
        # Initial: Total 2000000, Withdrawable 2000000
        # 1. Deposit 1000000 -> Total 3000000, Withdrawable 3000000
        # 2. Fee 250000 -> Total 2750000, Withdrawable 2750000
        # 3. Prize 500000 -> Total 3250000, Withdrawable 3250000
        # 4. Withdraw 1200000 -> Total 2050000, Withdrawable 2050000
        self.assertEqual(self.wallet.total_balance, Decimal("2050000.00"))
        self.assertEqual(self.wallet.withdrawable_balance, Decimal("2050000.00"))


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
        self.assertEqual(
            Decimal(response.data["total_balance"]), self.wallet.total_balance
        )

    def test_cannot_get_other_user_wallet_details(self):
        """Test that a user cannot retrieve another user's wallet details."""
        other_user = User.objects.create_user(
            username="otheruser", password="password", phone_number="+4445556666"
        )
        other_wallet_url = f"/api/wallet/wallets/{other_user.wallet.id}/"
        response = self.client.get(other_wallet_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class DepositAPITests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            password="password",
            phone_number="+98123456789",
            email="test@example.com",
        )
        self.client.force_authenticate(user=self.user)
        self.deposit_url = "/api/wallet/deposit/"

    @patch("wallet.views.ZibalService")
    def test_deposit_request_successful(self, MockZibalService):
        """
        Test that a deposit request is handled successfully and returns a payment URL.
        """
        mock_zibal_instance = MockZibalService.return_value
        mock_zibal_instance.create_payment.return_value = {
            "result": 100,
            "trackId": "test-track-id",
        }
        mock_zibal_instance.generate_payment_url.return_value = (
            "https://gateway.zibal.ir/start/test-track-id"
        )

        deposit_amount = Decimal("50000.00")
        response = self.client.post(
            self.deposit_url, {"amount": deposit_amount}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("payment_url", response.data)
        self.assertTrue(
            Transaction.objects.filter(
                wallet=self.user.wallet,
                amount=deposit_amount,
                authority="test-track-id",
                status="pending",
            ).exists()
        )

    @patch("wallet.views.uuid.uuid4", return_value="test-order-id")
    @patch("wallet.views.ZibalService")
    def test_deposit_request_zibal_error(self, MockZibalService, mock_uuid):
        """
        Test how the system handles an error from Zibal on payment creation.
        """
        mock_zibal_instance = MockZibalService.return_value
        mock_zibal_instance.create_payment.return_value = {
            "result": 102,
            "message": "merchant not found",
        }

        response = self.client.post(
            self.deposit_url, {"amount": Decimal("50000.00")}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertEqual(response.data["error"], "merchant not found")
        self.assertTrue(
            Transaction.objects.filter(
                wallet=self.user.wallet,
                order_id="test-order-id",
                status="failed",
            ).exists()
        )


class VerifyDepositAPITests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            password="password",
            phone_number="+98123456789",
            email="test@example.com",
        )
        self.wallet = self.user.wallet
        self.transaction = Transaction.objects.create(
            wallet=self.wallet,
            amount=Decimal("50000.00"),
            transaction_type="deposit",
            authority="test-track-id",
            order_id="test-order-id",
            status="pending",
        )
        self.verify_url = "/api/wallet/verify-deposit/"

    @patch("wallet.views.ZibalService.verify_payment")
    def test_verify_deposit_successful(self, mock_verify_payment):
        """
        Test successful deposit verification.
        """
        mock_verify_payment.return_value = {
            "result": 100,
            "paidAt": "2023-11-20T12:00:00Z",
            "refNumber": "test-ref-number",
        }
        initial_balance = self.wallet.total_balance

        response = self.client.get(
            self.verify_url,
            {"trackId": "test-track-id", "success": "1", "orderId": "test-order-id"},
        )

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.transaction.refresh_from_db()
        self.wallet.refresh_from_db()
        self.assertEqual(self.transaction.status, "success")
        self.assertEqual(self.transaction.ref_number, "test-ref-number")
        self.assertEqual(
            self.wallet.total_balance, initial_balance + self.transaction.amount
        )

    @patch("wallet.views.ZibalService.verify_payment")
    def test_verify_deposit_failed_by_user_cancellation(self, mock_verify_payment):
        """
        Test deposit verification when the user cancels the payment (success=0).
        """
        initial_balance = self.wallet.total_balance

        response = self.client.get(
            self.verify_url,
            {"trackId": "test-track-id", "success": "0", "orderId": "test-order-id"},
        )

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.transaction.refresh_from_db()
        self.wallet.refresh_from_db()
        self.assertEqual(self.transaction.status, "failed")
        self.assertEqual(self.wallet.total_balance, initial_balance)
        # Verify that verify_payment was not even called
        mock_verify_payment.assert_not_called()

    @patch("wallet.views.ZibalService.verify_payment")
    def test_verify_deposit_failed_bad_result(self, mock_verify_payment):
        """
        Test deposit verification fails if 'result' is not 100.
        """
        mock_verify_payment.return_value = {
            "result": 102,
            "message": "Verification failed",
        }
        initial_balance = self.wallet.total_balance

        response = self.client.get(
            self.verify_url,
            {"trackId": "test-track-id", "success": "1", "orderId": "test-order-id"},
        )

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.transaction.refresh_from_db()
        self.wallet.refresh_from_db()
        self.assertEqual(self.transaction.status, "failed")
        self.assertEqual(self.wallet.total_balance, initial_balance)

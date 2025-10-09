import json
from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .models import Transaction, Wallet
from .serializers import PaymentSerializer
from .services import ZarinpalService
from zarinpal.models import CurrencyEnum

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


class ZarinpalServiceTests(SimpleTestCase):
    @patch("wallet.services.RequestInput")
    @patch("wallet.services.ZarinPal")
    def test_create_payment_serializes_currency_enum(
        self, mock_zarinpal_cls, mock_request_input
    ):
        mock_zarinpal = mock_zarinpal_cls.return_value
        response_data = {"data": {"currency": CurrencyEnum.IRR.value}}
        mock_response = Mock()
        mock_response.model_dump_json.return_value = json.dumps(response_data)
        mock_zarinpal.request.return_value = mock_response

        service = ZarinpalService()
        result = service.create_payment(
            amount=1000,
            description="desc",
            callback_url="https://callback.test",
            currency=CurrencyEnum.IRR,
        )

        mock_request_input.assert_called_once()
        self.assertEqual(
            mock_request_input.call_args.kwargs["currency"], CurrencyEnum.IRR.value
        )
        self.assertEqual(result, response_data)

    @patch("wallet.services.VerifyInput")
    @patch("wallet.services.ZarinPal")
    def test_verify_payment_serializes_response(
        self, mock_zarinpal_cls, mock_verify_input
    ):
        mock_zarinpal = mock_zarinpal_cls.return_value
        response_data = {"data": {"currency": CurrencyEnum.IRT.value}}
        mock_response = Mock()
        mock_response.model_dump_json.return_value = json.dumps(response_data)
        mock_zarinpal.verify.return_value = mock_response

        service = ZarinpalService()
        result = service.verify_payment(amount=2000, authority="auth")

        mock_verify_input.assert_called_once_with(amount=2000, authority="auth")
        self.assertEqual(result, response_data)

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
        self.wallet.total_balance = Decimal("100.00")
        self.wallet.withdrawable_balance = Decimal("80.00")
        self.wallet.save()

    def test_deposit_updates_balance_correctly(self):
        """Test that a 'deposit' transaction correctly updates wallet balances."""
        transaction, error = process_transaction(
            user=self.user, amount=Decimal("50.00"), transaction_type="deposit"
        )
        self.assertIsNone(error)
        self.assertIsNotNone(transaction)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.total_balance, Decimal("150.00"))
        self.assertEqual(self.wallet.withdrawable_balance, Decimal("130.00"))

    def test_prize_updates_balance_correctly(self):
        """Test that a 'prize' transaction correctly updates wallet balances."""
        transaction, error = process_transaction(
            user=self.user, amount=Decimal("200.00"), transaction_type="prize"
        )
        self.assertIsNone(error)
        self.assertIsNotNone(transaction)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.total_balance, Decimal("300.00"))
        self.assertEqual(self.wallet.withdrawable_balance, Decimal("280.00"))

    def test_entry_fee_updates_balance_correctly(self):
        """Test that an 'entry_fee' transaction correctly updates wallet balances."""
        transaction, error = process_transaction(
            user=self.user, amount=Decimal("10.00"), transaction_type="entry_fee"
        )
        self.assertIsNone(error)
        self.assertIsNotNone(transaction)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.total_balance, Decimal("90.00"))
        self.assertEqual(self.wallet.withdrawable_balance, Decimal("70.00"))

    def test_withdrawal_updates_balance_correctly(self):
        """Test that a 'withdrawal' transaction correctly updates wallet balances."""
        transaction, error = process_transaction(
            user=self.user, amount=Decimal("30.00"), transaction_type="withdrawal"
        )
        self.assertIsNone(error)
        self.assertIsNotNone(transaction)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.total_balance, Decimal("70.00"))
        self.assertEqual(self.wallet.withdrawable_balance, Decimal("50.00"))

    def test_withdrawal_insufficient_funds(self):
        """Test that a withdrawal fails if funds are insufficient."""
        transaction, error = process_transaction(
            user=self.user, amount=Decimal("90.00"), transaction_type="withdrawal"
        )
        self.assertIsNone(transaction)
        self.assertIsNotNone(error)
        self.assertIn("Insufficient withdrawable balance", error)
        # Check that the balance has not changed
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.total_balance, Decimal("100.00"))

    def test_multiple_transactions_are_handled_correctly(self):
        """Test a sequence of transactions to ensure the final balance is correct."""
        # 1. Deposit 100
        process_transaction(
            user=self.user, amount=Decimal("100.00"), transaction_type="deposit"
        )
        # 2. Pay entry fee of 25
        process_transaction(
            user=self.user, amount=Decimal("25.00"), transaction_type="entry_fee"
        )
        # 3. Win prize of 50
        process_transaction(
            user=self.user, amount=Decimal("50.00"), transaction_type="prize"
        )
        # 4. Withdraw 120
        process_transaction(
            user=self.user, amount=Decimal("120.00"), transaction_type="withdrawal"
        )

        self.wallet.refresh_from_db()
        # Initial: Total 100, Withdrawable 80
        # 1. Deposit 100 -> Total 200, Withdrawable 180
        # 2. Fee 25 -> Total 175, Withdrawable 155
        # 3. Prize 50 -> Total 225, Withdrawable 205
        # 4. Withdraw 120 -> Total 105, Withdrawable 85
        self.assertEqual(self.wallet.total_balance, Decimal("105.00"))
        self.assertEqual(self.wallet.withdrawable_balance, Decimal("85.00"))


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

    @patch("wallet.views.ZarinpalService")
    def test_deposit_request_successful(self, MockZarinpalService):
        """
        Test that a deposit request is handled successfully and returns a payment URL.
        """
        mock_zarinpal_instance = MockZarinpalService.return_value
        mock_zarinpal_instance.create_payment.return_value = {
            "data": {"authority": "test-authority"},
            "error": None,
        }
        mock_zarinpal_instance.generate_payment_url.return_value = (
            "https://www.zarinpal.com/pg/StartPay/test-authority"
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
                authority="test-authority",
                status="pending",
            ).exists()
        )

    @patch("wallet.views.ZarinpalService")
    def test_deposit_request_zarinpal_error(self, MockZarinpalService):
        """
        Test how the system handles an error from Zarinpal on payment creation.
        """
        mock_zarinpal_instance = MockZarinpalService.return_value
        mock_zarinpal_instance.create_payment.return_value = {
            "data": None,
            "error": "Failed to connect to Zarinpal",
        }

        response = self.client.post(
            self.deposit_url, {"amount": Decimal("50000.00")}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertFalse(
            Transaction.objects.filter(wallet=self.user.wallet).exists()
        )

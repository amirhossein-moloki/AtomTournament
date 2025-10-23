from decimal import Decimal
from unittest.mock import patch
import requests

from django.test import TestCase

from users.models import User
from wallet.models import Transaction, Wallet
from wallet.services import (
    ZibalService,
    process_transaction,
    process_token_transaction,
)


class ZibalServiceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpassword",
            phone_number="+989123456789",
        )
        self.wallet = Wallet.objects.get(user=self.user)

    @patch("wallet.services.requests.post")
    def test_create_payment_success(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "result": 100,
            "trackId": "12345",
        }
        zibal = ZibalService()
        response = zibal.create_payment(
            amount=10000,
            description="Test payment",
            callback_url="http://test.com/callback",
            order_id="123",
        )
        self.assertEqual(response["result"], 100)
        self.assertEqual(response["trackId"], "12345")

    @patch("wallet.services.requests.post")
    def test_verify_payment_success(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"result": 100}
        zibal = ZibalService()
        response = zibal.verify_payment(track_id="12345")
        self.assertEqual(response["result"], 100)

    @patch("wallet.services.requests.post")
    def test_inquiry_payment_success(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"result": 100, "status": 1}
        zibal = ZibalService()
        response = zibal.inquiry_payment(track_id="12345")
        self.assertEqual(response["result"], 100)
        self.assertEqual(response["status"], 1)

    @patch("wallet.services.requests.post")
    def test_create_payment_failure(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "result": 101,
            "message": "Invalid merchant",
        }
        zibal = ZibalService()
        response = zibal.create_payment(
            amount=10000,
            description="Test payment",
            callback_url="http://test.com/callback",
            order_id="123",
        )
        self.assertEqual(response["result"], 101)
        self.assertEqual(response["message"], "Invalid merchant")

    @patch("wallet.services.requests.post")
    def test_create_payment_network_error(self, mock_post):
        mock_post.side_effect = requests.exceptions.RequestException("Network error")
        zibal = ZibalService()
        response = zibal.create_payment(1000, "desc", "url", "order")
        self.assertIn("error", response)
        self.assertEqual(response["error"], "Network error")

    def test_generate_payment_url(self):
        zibal = ZibalService()
        track_id = "12345"
        url = zibal.generate_payment_url(track_id)
        self.assertEqual(url, f"https://gateway.zibal.ir/start/{track_id}")


class ProcessTransactionTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpassword",
            phone_number="+989123456789",
        )
        self.wallet = Wallet.objects.get(user=self.user)

    def test_process_successful_deposit(self):
        amount = Decimal("10000.00")
        tx, error = process_transaction(
            self.user, amount, "deposit", "Test deposit"
        )
        self.assertIsNone(error)
        self.assertIsNotNone(tx)
        self.wallet.refresh_from_db()
        self.assertEqual(tx.status, "success")
        self.assertEqual(self.wallet.total_balance, amount)
        self.assertEqual(self.wallet.withdrawable_balance, amount)

    def test_process_failed_withdrawal_insufficient_funds(self):
        self.wallet.total_balance = Decimal("5000.00")
        self.wallet.withdrawable_balance = Decimal("5000.00")
        self.wallet.save()
        amount = Decimal("10000.00")
        tx, error = process_transaction(
            self.user, amount, "withdrawal", "Test withdrawal"
        )
        self.assertIsNotNone(error)
        self.assertIsNone(tx)


class ProcessTokenTransactionTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpassword",
            phone_number="+989123456789",
        )
        self.wallet = Wallet.objects.get(user=self.user)

    def test_process_successful_token_earned(self):
        initial_token_balance = self.wallet.token_balance
        amount = Decimal("100.00")
        tx, error = process_token_transaction(
            self.user, amount, "token_earned", "Earned tokens"
        )
        self.assertIsNone(error)
        self.assertIsNotNone(tx)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.token_balance, initial_token_balance + amount)

    def test_process_successful_token_spent(self):
        self.wallet.token_balance = Decimal("200.00")
        self.wallet.save()
        amount = Decimal("50.00")
        tx, error = process_token_transaction(
            self.user, amount, "token_spent", "Spent tokens"
        )
        self.assertIsNone(error)
        self.assertIsNotNone(tx)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.token_balance, Decimal("150.00"))

    def test_process_failed_token_spent_insufficient_funds(self):
        self.wallet.token_balance = Decimal("50.00")
        self.wallet.save()
        amount = Decimal("100.00")
        tx, error = process_token_transaction(
            self.user, amount, "token_spent", "Spent tokens"
        )
        self.assertIsNotNone(error)
        self.assertIsNone(tx)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.token_balance, Decimal("50.00"))

    def test_process_invalid_token_transaction_type(self):
        initial_token_balance = self.wallet.token_balance
        amount = Decimal("100.00")
        tx, error = process_token_transaction(
            self.user, amount, "invalid_type", "Invalid type"
        )
        self.assertIsNotNone(error)
        self.assertIsNone(tx)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.token_balance, initial_token_balance)

    def test_process_failed_withdrawal_minimum_amount(self):
        self.wallet.total_balance = Decimal("2000000.00")
        self.wallet.withdrawable_balance = Decimal("2000000.00")
        self.wallet.save()
        amount = Decimal("100.00")  # Below minimum
        tx, error = process_transaction(
            self.user, amount, "withdrawal", "Test withdrawal"
        )
        self.assertIsNotNone(error)
        self.assertIsNone(tx)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.total_balance, Decimal("2000000.00"))
        self.assertEqual(self.wallet.withdrawable_balance, Decimal("2000000.00"))

    def test_process_failed_withdrawal_frequency(self):
        self.wallet.total_balance = Decimal("3000000.00")
        self.wallet.withdrawable_balance = Decimal("3000000.00")
        self.wallet.save()
        amount = Decimal("1500000.00")
        process_transaction(self.user, amount, "withdrawal", "First withdrawal")
        tx, error = process_transaction(
            self.user, amount, "withdrawal", "Second withdrawal"
        )
        self.assertIsNotNone(error)
        self.assertIsNone(tx)

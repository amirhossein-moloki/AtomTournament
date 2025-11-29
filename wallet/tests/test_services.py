import unittest
from unittest.mock import patch, MagicMock
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.conf import settings

from wallet.services import ZibalService, process_transaction, verify_and_process_deposit
from wallet.models import Wallet, Transaction

User = get_user_model()

class ZibalServiceTests(TestCase):
    """Unit tests for the ZibalService class."""

    def setUp(self):
        self.service = ZibalService()
        # Mock settings
        settings.ZIBAL_ACCESS_TOKEN = "test_token"
        settings.ZIBAL_MERCHANT_ID = "zibal_test"

    @patch('requests.post')
    def test_create_payment_success(self, mock_post):
        """Test successful payment creation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": 100, "trackId": 12345}
        mock_post.return_value = mock_response

        response = self.service.create_payment(1000, "Test", "http://callback.url", "order1")
        self.assertEqual(response["result"], 100)
        self.assertEqual(response["trackId"], 12345)

    @patch('requests.post')
    def test_verify_payment_success(self, mock_post):
        """Test successful payment verification."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": 100, "refNumber": 54321}
        mock_post.return_value = mock_response

        response = self.service.verify_payment(12345, 1000)
        self.assertEqual(response["result"], 100)
        self.assertEqual(response["refNumber"], 54321)

    @patch('requests.get')
    def test_list_wallets_success(self, mock_get):
        """Test successfully listing wallets."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": 1, "data": [{"id": 1, "name": "Main Wallet"}]}
        mock_get.return_value = mock_response

        response = self.service.list_wallets()
        self.assertEqual(response["result"], 1)
        self.assertIsInstance(response["data"], list)
        self.assertEqual(response["data"][0]["name"], "Main Wallet")

    @patch('requests.post')
    def test_request_refund_success(self, mock_post):
        """Test successful refund request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": 1, "data": {"refundId": "refund_abc"}}
        mock_post.return_value = mock_response

        response = self.service.request_refund(track_id=12345, amount=1000)
        self.assertEqual(response["result"], 1)
        self.assertEqual(response["data"]["refundId"], "refund_abc")

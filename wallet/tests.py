import json
from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .models import Transaction, Wallet, WithdrawalRequest
from .serializers import PaymentSerializer, CreateWithdrawalRequestSerializer
from .services import ZibalService
from django.conf import settings

User = get_user_model()


class SerializerTests(SimpleTestCase):
    def test_payment_serializer_amount_valid(self):
        serializer = PaymentSerializer(data={"amount": "1234567890"})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_payment_serializer_amount_invalid(self):
        serializer = PaymentSerializer(data={"amount": "12345678901"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("Ensure that there are no more than 10 digits in total.", str(serializer.errors))

    def test_create_withdrawal_request_serializer_valid(self):
        data = {
            "amount": "50000",
            "card_number": "6037997599999999",
            "sheba_number": "IR120120000000001234567890"
        }
        serializer = CreateWithdrawalRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_create_withdrawal_request_serializer_invalid_card(self):
        data = {"amount": "50000", "card_number": "1234", "sheba_number": "IR120120000000001234567890"}
        serializer = CreateWithdrawalRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("card_number", serializer.errors)

class WalletSignalTests(TestCase):
    def test_wallet_is_created_for_new_user(self):
        initial_wallet_count = Wallet.objects.count()
        user = User.objects.create_user(
            username="newuser", password="password", phone_number="+9876543210"
        )
        self.assertTrue(hasattr(user, "wallet"))
        self.assertEqual(Wallet.objects.count(), initial_wallet_count + 1)


class WalletAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password", phone_number="+989121112233")
        self.admin = User.objects.create_superuser(username="admin", password="password", phone_number="+989120000000")
        self.wallet = self.user.wallet

    @patch("wallet.views.WalletService.create_deposit")
    def test_deposit_api_success(self, mock_create_deposit):
        mock_create_deposit.return_value = "http://payment-url.com"
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/wallet/deposit/", {"amount": "50000"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["payment_url"], "http://payment-url.com")
        mock_create_deposit.assert_called_once()

    @patch("wallet.views.WalletService.create_withdrawal_request")
    def test_create_withdrawal_request_api_success(self, mock_create_withdrawal):
        # Mock the service to return a dummy WithdrawalRequest object
        mock_withdrawal = WithdrawalRequest(id=1, user=self.user, amount=Decimal("50000"))
        mock_create_withdrawal.return_value = mock_withdrawal

        self.client.force_authenticate(user=self.user)
        data = {
            "amount": "50000",
            "card_number": "6037997599999999",
            "sheba_number": "IR120120000000001234567890"
        }
        response = self.client.post("/api/wallet/withdrawal-requests/", data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_create_withdrawal.assert_called_once()
        self.assertEqual(response.data['amount'], '50000.00')


    @patch("wallet.services.WalletService.approve_withdrawal_request")
    def test_admin_approve_withdrawal_request(self, mock_approve):
        request = WithdrawalRequest.objects.create(user=self.user, amount=Decimal("50000"))
        # We need to return the instance from the mock to be serialized
        mock_approve.return_value = request

        self.client.force_authenticate(user=self.admin)
        url = f"/api/wallet/admin/withdrawal-requests/{request.id}/"
        response = self.client.patch(url, {"status": WithdrawalRequest.Status.APPROVED})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_approve.assert_called_once_with(request)

    @patch("wallet.services.WalletService.reject_withdrawal_request")
    def test_admin_reject_withdrawal_request(self, mock_reject):
        request = WithdrawalRequest.objects.create(user=self.user, amount=Decimal("50000"), status=WithdrawalRequest.Status.PENDING)

        # When reject is called, the status will be updated on the instance.
        # So we can modify the instance and return it.
        request.status = WithdrawalRequest.Status.REJECTED
        mock_reject.return_value = request

        self.client.force_authenticate(user=self.admin)
        url = f"/api/wallet/admin/withdrawal-requests/{request.id}/"
        response = self.client.patch(url, {"status": WithdrawalRequest.Status.REJECTED})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_reject.assert_called_once()
        # You can access the first argument of the first call to the mock like this:
        self.assertEqual(mock_reject.call_args[0][0].id, request.id)

    @patch("wallet.tasks.verify_deposit_task.delay")
    def test_verify_deposit_api_enqueues_task(self, mock_delay):
        tx = Transaction.objects.create(
            wallet=self.wallet,
            amount=Decimal("50000"),
            order_id="order1",
            authority="track1"
        )
        url = f"/api/wallet/verify-deposit/?trackId=track1&success=1&orderId=order1"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        mock_delay.assert_called_once_with(track_id='track1', order_id='order1')

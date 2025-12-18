import json
from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework import status
from rest_framework.settings import reload_api_settings
from rest_framework.test import APIClient, APITestCase

from .models import Transaction, Wallet, WithdrawalRequest
from .serializers import (
    PaymentSerializer,
    CreateWithdrawalRequestSerializer,
    WithdrawalRequestSerializer,
)
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


class WithdrawalRequestSerializerTests(TestCase):
    def test_serializer_includes_card_and_sheba_numbers(self):
        user = User.objects.create_user(
            username="withdrawal-user",
            password="password",
            phone_number="+989121111111",
        )
        wallet = user.wallet
        wallet.card_number = "6037997599999999"
        wallet.sheba_number = "IR120120000000001234567890"
        wallet.save()

        request = WithdrawalRequest.objects.create(
            user=user,
            amount=Decimal("50000"),
        )

        serialized = WithdrawalRequestSerializer(request).data

        self.assertEqual(serialized["card_number"], wallet.card_number)
        self.assertEqual(serialized["sheba_number"], wallet.sheba_number)

class WalletSignalTests(TestCase):
    def test_wallet_is_created_for_new_user(self):
        initial_wallet_count = Wallet.objects.count()
        user = User.objects.create_user(
            username="newuser", password="password", phone_number="+9876543210"
        )
        self.assertTrue(hasattr(user, "wallet"))
        self.assertEqual(Wallet.objects.count(), initial_wallet_count + 1)


@override_settings(
    REST_FRAMEWORK={
        "DEFAULT_THROTTLE_RATES": {
            "very_strict": "1000/min",
            "strict": "1000/min",
            "medium": "1000/min",
        }
    }
)
class WalletAPITests(APITestCase):
    def setUp(self):
        reload_api_settings(setting="REST_FRAMEWORK")
        self.user = User.objects.create_user(username="testuser", password="password", phone_number="+989121112233")
        self.admin = User.objects.create_superuser(username="admin", password="password", phone_number="+989120000000")
        self.wallet = self.user.wallet
        self.other_user = User.objects.create_user(
            username="otheruser", password="password", phone_number="+989121112234"
        )
        self.other_wallet = self.other_user.wallet

    @patch("wallet.views.WalletService.create_deposit")
    def test_deposit_api_success(self, mock_create_deposit):
        mock_create_deposit.return_value = "http://payment-url.com"
        self.client.force_authenticate(user=self.user)
        with patch("wallet.views.DepositAPIView.throttle_classes", []):
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

    @patch("wallet.views.WalletService.verify_and_process_deposit")
    def test_verify_deposit_api_processes_immediately(self, mock_verify):
        tx = Transaction.objects.create(
            wallet=self.wallet,
            amount=Decimal("50000"),
            order_id="order1",
            authority="track1",
            status=Transaction.Status.PENDING,
        )

        def mark_success(**kwargs):
            Transaction.objects.filter(id=tx.id).update(status=Transaction.Status.SUCCESS)

        mock_verify.side_effect = mark_success

        url = f"/api/wallet/verify-deposit/?trackId=track1&success=1&orderId=order1"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        mock_verify.assert_called_once_with(track_id="track1", order_id="order1")

        tx.refresh_from_db()
        self.assertEqual(tx.status, Transaction.Status.SUCCESS)

    def test_wallet_list_scoped_to_request_user(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/wallet/wallets/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.wallet.id)

    def test_wallet_retrieve_other_user_not_found(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"/api/wallet/wallets/{self.other_wallet.id}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_transaction_list_scoped_to_request_user(self):
        Transaction.objects.create(wallet=self.wallet, amount=Decimal("100"), transaction_type=Transaction.TransactionType.DEPOSIT)
        Transaction.objects.create(wallet=self.other_wallet, amount=Decimal("200"), transaction_type=Transaction.TransactionType.DEPOSIT)

        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/wallet/transactions/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["wallet"], self.wallet.id)

    def test_transaction_retrieve_other_user_not_found(self):
        transaction = Transaction.objects.create(wallet=self.other_wallet, amount=Decimal("300"), transaction_type=Transaction.TransactionType.DEPOSIT)

        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"/api/wallet/transactions/{transaction.id}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

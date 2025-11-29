from unittest.mock import patch
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

from wallet.models import Wallet, Transaction, Refund

User = get_user_model()

class WalletAPITests(APITestCase):
    """
    Functional tests for the new wallet API views.
    """

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword', phone_number='9123456789')
        self.admin = User.objects.create_superuser(username='admin', password='adminpass', phone_number='9876543210')
        self.wallet = Wallet.objects.create(user=self.user, total_balance=50000, withdrawable_balance=50000)

    @patch('wallet.views.ZibalService.request_refund')
    def test_refund_transaction_success(self, mock_request_refund):
        """
        Ensure user can request a refund for their own successful transaction.
        """
        # Mock the response from ZibalService
        mock_request_refund.return_value = {
            "result": 1,
            "message": "استرداد با موفقیت ثبت شد",
            "data": {"refundId": "zibal_refund_123"}
        }

        # Create a successful transaction to be refunded
        tx = Transaction.objects.create(
            wallet=self.wallet,
            amount=20000,
            transaction_type='deposit',
            status='success',
            authority='track_12345'
        )

        url = reverse('refund')
        data = {'track_id': 'track_12345', 'amount': 20000}

        self.client.force_authenticate(user=self.user)
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'درخواست استرداد با موفقیت ثبت شد.')

        # Verify refund object was created and transaction was updated
        self.assertTrue(Refund.objects.filter(transaction=tx).exists())
        refund = Refund.objects.get(transaction=tx)
        self.assertEqual(refund.status, Refund.Status.PENDING) # Check status is pending
        tx.refresh_from_db()
        self.assertTrue(tx.is_refunded)

    @patch('wallet.views.ZibalService.request_refund')
    def test_refund_fails_if_zibal_api_returns_error(self, mock_request_refund):
        """
        Ensure the refund process handles errors from the Zibal API.
        """
        mock_request_refund.return_value = {"result": 0, "message": "API Error"}
        tx = Transaction.objects.create(wallet=self.wallet, amount=10000, status='success', authority='track_api_error')

        url = reverse('refund')
        data = {'track_id': 'track_api_error'}
        self.client.force_authenticate(user=self.user)
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Refund.objects.filter(transaction=tx).exists())
        tx.refresh_from_db()
        self.assertFalse(tx.is_refunded)

    def test_refund_fails_for_already_refunded_transaction(self):
        """
        Ensure a transaction cannot be refunded more than once.
        """
        tx = Transaction.objects.create(wallet=self.wallet, amount=10000, status='success', authority='track_double_refund', is_refunded=True)

        url = reverse('refund')
        data = {'track_id': 'track_double_refund'}
        self.client.force_authenticate(user=self.user)
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'این تراکنش قبلا استرداد شده است.')

    def test_refund_transaction_not_found(self):
        """
        Ensure refund fails if the transaction does not exist.
        """
        url = reverse('refund')
        data = {'track_id': 'non_existent_track_id'}

        self.client.force_authenticate(user=self.user)
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('wallet.views.ZibalService.list_wallets')
    def test_admin_can_list_zibal_wallets(self, mock_list_wallets):
        """
        Ensure an admin user can fetch the list of Zibal wallets.
        """
        mock_list_wallets.return_value = {
            "result": 1,
            "data": [{"id": 1, "name": "Main Merchant Wallet", "balance": 1000000}]
        }

        url = reverse('zibal-wallets')
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(response.data[0]['name'], 'Main Merchant Wallet')

    def test_normal_user_cannot_list_zibal_wallets(self):
        """
        Ensure a non-admin user cannot access the Zibal wallets list.
        """
        url = reverse('zibal-wallets')
        self.client.force_authenticate(user=self.user)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.test import override_settings

from .models import Wallet

User = get_user_model()


@override_settings(AXES_ENABLED=False)
class WalletTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpassword"
        )
        self.wallet = Wallet.objects.create(user=self.user, total_balance=100, withdrawable_balance=100)
        self.client.login(username="testuser", password="testpassword")

    @patch("wallet.services.ZarinpalService.create_payment")
    def test_create_payment(self, mock_create_payment):
        mock_create_payment.return_value = {
            "data": {"authority": "test_authority"},
            "errors": [],
        }
        url = reverse("payment-list")
        data = {"amount": 50000}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("payment_url", response.data)

    @patch("wallet.services.ZarinpalService.verify_payment")
    def test_verify_payment(self, mock_verify_payment):
        mock_verify_payment.return_value = {"data": {"code": 100}, "errors": []}
        authority = "test_authority"
        amount = 50000
        session = self.client.session
        session[f"payment_{authority}"] = amount
        session.save()
        url = reverse("payment-verify") + f"?Authority={authority}&Status=OK"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.total_balance, 100 + amount)

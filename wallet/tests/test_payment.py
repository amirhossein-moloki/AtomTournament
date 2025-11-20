import uuid
from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User
from wallet.models import Transaction, Wallet, WithdrawalRequest


class PaymentAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpassword",
            phone_number="+989123456789",
        )
        self.wallet = Wallet.objects.get(user=self.user)
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        self.deposit_url = reverse("deposit")
        self.verify_deposit_url = reverse("verify_deposit")
        self.withdraw_url = reverse("create-withdrawal-request")

    @patch("wallet.views.ZibalService")
    def test_deposit_success(self, MockZibalService):
        track_id = str(uuid.uuid4())
        mock_zibal_instance = MockZibalService.return_value
        mock_zibal_instance.create_payment.return_value = {
            "result": 100,
            "trackId": track_id,
        }
        mock_zibal_instance.generate_payment_url.return_value = (
            f"https://gateway.zibal.ir/start/{track_id}"
        )

        data = {"amount": "10000.00"}
        response = self.client.post(self.deposit_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("payment_url", response.data)
        self.assertTrue(
            Transaction.objects.filter(
                wallet=self.wallet, authority=track_id, status="pending"
            ).exists()
        )

    def test_deposit_invalid_amount(self):
        data = {"amount": "-100.00"}
        response = self.client.post(self.deposit_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("wallet.services.ZibalService")
    def test_verify_deposit_success(self, MockZibalService):
        track_id = str(uuid.uuid4())
        order_id = str(uuid.uuid4())
        tx = Transaction.objects.create(
            wallet=self.wallet,
            amount=Decimal("10000.00"),
            authority=track_id,
            order_id=order_id,
            status="pending",
            transaction_type="deposit",
        )
        mock_zibal_instance = MockZibalService.return_value
        mock_zibal_instance.verify_payment.return_value = {"result": 100}

        response = self.client.get(
            f"{self.verify_deposit_url}?trackId={track_id}&success=1&orderId={order_id}"
        )

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, settings.ZIBAL_PAYMENT_SUCCESS_URL)

        tx.refresh_from_db()
        self.assertEqual(tx.status, "success")

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.total_balance, Decimal("10000.00"))
        self.assertEqual(self.wallet.withdrawable_balance, Decimal("10000.00"))

    @patch("wallet.services.ZibalService")
    def test_verify_deposit_failed_from_zibal(self, MockZibalService):
        track_id = str(uuid.uuid4())
        order_id = str(uuid.uuid4())
        tx = Transaction.objects.create(
            wallet=self.wallet,
            amount=Decimal("10000.00"),
            authority=track_id,
            order_id=order_id,
            status="pending",
            transaction_type="deposit",
        )
        mock_zibal_instance = MockZibalService.return_value
        mock_zibal_instance.verify_payment.return_value = {"result": 202}

        response = self.client.get(
            f"{self.verify_deposit_url}?trackId={track_id}&success=1&orderId={order_id}"
        )

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, settings.ZIBAL_PAYMENT_FAILED_URL)

        tx.refresh_from_db()
        self.assertEqual(tx.status, "failed")

    def test_verify_deposit_failed_by_user_cancellation(self):
        track_id = str(uuid.uuid4())
        order_id = str(uuid.uuid4())
        tx = Transaction.objects.create(
            wallet=self.wallet,
            amount=Decimal("10000.00"),
            authority=track_id,
            order_id=order_id,
            status="pending",
            transaction_type="deposit",
        )

        response = self.client.get(
            f"{self.verify_deposit_url}?trackId={track_id}&success=0&orderId={order_id}"
        )

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, settings.ZIBAL_PAYMENT_FAILED_URL)

        tx.refresh_from_db()
        self.assertEqual(tx.status, "failed")

    def test_verify_deposit_transaction_not_found(self):
        track_id = str(uuid.uuid4())
        order_id = str(uuid.uuid4())
        response = self.client.get(
            f"{self.verify_deposit_url}?trackId={track_id}&success=1&orderId={order_id}"
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, settings.ZIBAL_PAYMENT_FAILED_URL)

    def test_withdraw_success(self):
        WithdrawalRequest.objects.filter(user=self.user).delete()
        self.wallet.total_balance = Decimal("5000.00")
        self.wallet.withdrawable_balance = Decimal("2000000.00")
        self.wallet.save()

        data = {"amount": "1500000.00", "card_number": "1234567890123456", "sheba_number": "IR123456789012345678901234"}
        response = self.client.post(self.withdraw_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.withdrawable_balance, Decimal("500000.00"))

    def test_withdraw_insufficient_funds(self):
        self.wallet.total_balance = Decimal("1000.00")
        self.wallet.withdrawable_balance = Decimal("1000.00")
        self.wallet.save()

        data = {"amount": "2000.00", "card_number": "1234567890123456", "sheba_number": "IR123456789012345678901234"}
        response = self.client.post(self.withdraw_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.withdrawable_balance, Decimal("1000.00"))

    def test_withdraw_invalid_amount(self):
        data = {"amount": "-500.00", "card_number": "1234567890123456", "sheba_number": "IR123456789012345678901234"}
        response = self.client.post(self.withdraw_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

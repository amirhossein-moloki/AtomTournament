from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework.exceptions import ValidationError, NotFound

from .models import Wallet, WithdrawalRequest, Transaction
from .services import WalletService

User = get_user_model()


class WalletServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="password", phone_number="+989123456789"
        )
        self.wallet = Wallet.objects.get(user=self.user)
        self.service = WalletService(user=self.user)

    def test_get_wallet_success(self):
        wallet = self.service.get_wallet()
        self.assertEqual(wallet, self.wallet)

    def test_get_wallet_not_found(self):
        other_user = User.objects.create_user(
            username="otheruser", password="password", phone_number="+989120000000"
        )
        service = WalletService(user=other_user)
        # Manually delete the wallet to simulate the condition
        Wallet.objects.filter(user=other_user).delete()
        with self.assertRaises(NotFound):
            service.get_wallet()

    @patch("wallet.services.ZibalService")
    def test_create_deposit_success(self, MockZibalService):
        mock_zibal = MockZibalService.return_value
        mock_zibal.create_payment.return_value = {"trackId": "12345"}
        mock_zibal.generate_payment_url.return_value = "http://payment-url.com"

        def mock_callback_builder(path):
            return f"http://testserver{path}"

        amount = Decimal("50000")
        payment_url = self.service.create_deposit(amount, mock_callback_builder)

        self.assertEqual(payment_url, "http://payment-url.com")
        self.assertTrue(
            Transaction.objects.filter(
                wallet=self.wallet,
                amount=amount,
                status=Transaction.Status.PENDING,
                authority="12345",
            ).exists()
        )

    @patch("wallet.services.ZibalService")
    def test_create_deposit_zibal_failure(self, MockZibalService):
        mock_zibal = MockZibalService.return_value
        mock_zibal.create_payment.return_value = {
            "result": 102,
            "message": "merchant not found",
        }

        with self.assertRaises(ValidationError) as cm:
            self.service.create_deposit(
                Decimal("50000"), lambda p: f"http://testserver{p}"
            )

        self.assertEqual(str(cm.exception.detail[0]), "merchant not found")
        self.assertTrue(
            Transaction.objects.filter(
                wallet=self.wallet, status=Transaction.Status.FAILED
            ).exists()
        )

    def test_create_withdrawal_request_success(self):
        self.wallet.withdrawable_balance = Decimal("100000")
        self.wallet.save()

        amount = settings.MINIMUM_WITHDRAWAL_AMOUNT
        request = self.service.create_withdrawal_request(
            amount, "1234567812345678", "IR123456789012345678901234"
        )

        self.assertEqual(request.amount, amount)
        self.assertEqual(request.user, self.user)
        self.wallet.refresh_from_db()
        self.assertEqual(
            self.wallet.withdrawable_balance, Decimal("100000") - amount
        )

    def test_create_withdrawal_insufficient_balance(self):
        self.wallet.withdrawable_balance = Decimal("10000")
        self.wallet.save()

        with self.assertRaisesMessage(ValidationError, "موجودی قابل برداشت کافی نیست."):
            self.service.create_withdrawal_request(
                Decimal("20000"), "1234", "IR1234"
            )

    def test_create_withdrawal_below_minimum(self):
        with self.assertRaises(ValidationError):
            self.service.create_withdrawal_request(
                settings.MINIMUM_WITHDRAWAL_AMOUNT - 1, "1234", "IR1234"
            )

    def test_approve_withdrawal_request(self):
        request = WithdrawalRequest.objects.create(
            user=self.user, amount=Decimal("50000")
        )
        updated_request = WalletService.approve_withdrawal_request(request)
        self.assertEqual(updated_request.status, WithdrawalRequest.Status.APPROVED)
        self.assertTrue(
            Transaction.objects.filter(
                wallet__user=self.user,
                transaction_type=Transaction.TransactionType.WITHDRAWAL,
                status=Transaction.Status.SUCCESS,
            ).exists()
        )

    def test_reject_withdrawal_request(self):
        self.wallet.total_balance = Decimal("100000")
        self.wallet.save()
        request = WithdrawalRequest.objects.create(
            user=self.user, amount=Decimal("50000")
        )

        # Simulate balance deduction at time of request creation
        self.wallet.total_balance -= request.amount
        self.wallet.save()

        updated_request = WalletService.reject_withdrawal_request(request)
        self.assertEqual(updated_request.status, WithdrawalRequest.Status.REJECTED)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.total_balance, Decimal("100000"))

    @patch("wallet.services.ZibalService")
    def test_verify_and_process_deposit_success(self, MockZibalService):
        mock_zibal = MockZibalService.return_value
        mock_zibal.verify_payment.return_value = {
            "result": 100,
            "refNumber": "ref123",
        }
        tx = Transaction.objects.create(
            wallet=self.wallet,
            amount=Decimal("50000"),
            order_id="order1",
            authority="track1",
            status=Transaction.Status.PENDING,
        )
        initial_balance = self.wallet.total_balance

        WalletService.verify_and_process_deposit(track_id="track1", order_id="order1")

        tx.refresh_from_db()
        self.wallet.refresh_from_db()
        self.assertEqual(tx.status, Transaction.Status.SUCCESS)
        self.assertEqual(self.wallet.total_balance, initial_balance + tx.amount)

    def test_process_transaction_debit_success(self):
        self.wallet.withdrawable_balance = Decimal("1000")
        self.wallet.save()

        tx = WalletService.process_transaction(
            self.user, Decimal("500"), Transaction.TransactionType.ENTRY_FEE, "Test Fee"
        )
        self.wallet.refresh_from_db()
        self.assertEqual(tx.amount, Decimal("500"))
        self.assertEqual(self.wallet.withdrawable_balance, Decimal("500"))

    def test_process_transaction_credit_success(self):
        initial_balance = self.wallet.total_balance
        tx = WalletService.process_transaction(
            self.user, Decimal("500"), Transaction.TransactionType.PRIZE, "Test Prize"
        )
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.total_balance, initial_balance + Decimal("500"))

    def test_process_transaction_insufficient_funds(self):
        self.wallet.withdrawable_balance = Decimal("100")
        self.wallet.save()
        with self.assertRaises(ValidationError):
            WalletService.process_transaction(
                self.user, Decimal("200"), Transaction.TransactionType.ENTRY_FEE
            )

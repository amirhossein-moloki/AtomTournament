"""
Tests for the wallet API endpoints in wallet/views.py.
Covers deposit and withdrawal flows, transaction verification,
and error handling, with mocked payment gateway interactions.
"""
import pytest
from django.urls import reverse
from rest_framework import status
from wallet.models import Transaction, Wallet

# Define dummy URLs for redirection tests
SUCCESS_URL = "https://example.com/success"
FAILED_URL = "https://example.com/failed"


@pytest.mark.django_db
class TestDepositAPIView:
    def test_create_deposit_success(
        self, authenticated_client, default_user, mock_zibal_service, settings
    ):
        """
        GIVEN a user with a wallet
        WHEN they make a valid deposit request
        THEN a pending transaction should be created and a payment URL returned.
        """
        settings.ZIBAL_MERCHANT_ID = "zibal"
        url = reverse("deposit")
        data = {"amount": 50000}

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert "payment_url" in response.data
        assert "https://gateway.zibal.ir/start/123456" in response.data["payment_url"]

        tx = Transaction.objects.get(wallet__user=default_user)
        assert tx.amount == 50000
        assert tx.status == "pending"
        assert tx.authority == "123456"
        mock_zibal_service.return_value.create_payment.assert_called_once()

    def test_create_deposit_gateway_fails(
        self, authenticated_client, default_user, mock_zibal_service
    ):
        """
        GIVEN a user with a wallet
        WHEN the payment gateway fails to create a transaction
        THEN the transaction status should be 'failed' and an error returned.
        """
        mock_zibal_service.return_value.create_payment.return_value = {
            "result": 101,
            "message": "Gateway error",
        }
        url = reverse("deposit")
        data = {"amount": 50000}

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Gateway error"

        tx = Transaction.objects.get(wallet__user=default_user)
        assert tx.status == "failed"

    def test_create_deposit_unauthenticated(self, api_client):
        """
        GIVEN an unauthenticated user
        WHEN they attempt to make a deposit
        THEN they should receive a 401 Unauthorized error.
        """
        url = reverse("deposit")
        data = {"amount": 50000}
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_deposit_invalid_amount(self, authenticated_client):
        """
        GIVEN an authenticated user
        WHEN they request a deposit with an invalid amount
        THEN they should receive a 400 Bad Request error.
        """
        url = reverse("deposit")
        data = {"amount": -100}  # Invalid amount
        response = authenticated_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestVerifyDepositAPIView:
    @pytest.fixture(autouse=True)
    def override_redirect_urls(self, settings):
        """Override redirect URLs for all tests in this class."""
        settings.ZIBAL_PAYMENT_SUCCESS_URL = SUCCESS_URL
        settings.ZIBAL_PAYMENT_FAILED_URL = FAILED_URL

    @pytest.fixture
    def pending_tx(self, default_user):
        """Creates a pending transaction for verification tests."""
        wallet = default_user.wallet
        return Transaction.objects.create(
            wallet=wallet,
            amount=50000,
            transaction_type="deposit",
            status="pending",
            order_id="test_order_123",
            authority="test_track_123",
        )

    def test_verify_deposit_success(
        self, api_client, pending_tx, mock_zibal_service
    ):
        """
        GIVEN a pending transaction
        WHEN the user is redirected from the gateway after a successful payment
        THEN the transaction should be marked 'success' and the wallet balance updated.
        """
        url = f"{reverse('verify_deposit')}?success=1&trackId={pending_tx.authority}&orderId={pending_tx.order_id}"
        mock_zibal_service.return_value.verify_payment.return_value = {
            "result": 100,
            "refNumber": "ref12345",
        }
        initial_balance = pending_tx.wallet.total_balance

        response = api_client.get(url)

        assert response.status_code == status.HTTP_302_FOUND
        assert response.url == SUCCESS_URL

        pending_tx.refresh_from_db()
        assert pending_tx.status == "success"
        assert pending_tx.ref_number == "ref12345"

        wallet = pending_tx.wallet
        wallet.refresh_from_db()
        assert wallet.total_balance == initial_balance + pending_tx.amount

    def test_verify_deposit_user_canceled(self, api_client, pending_tx):
        """
        GIVEN a pending transaction
        WHEN the user cancels the payment on the gateway page
        THEN the transaction should be marked 'failed'.
        """
        url = f"{reverse('verify_deposit')}?success=0&trackId={pending_tx.authority}&orderId={pending_tx.order_id}"
        initial_balance = pending_tx.wallet.total_balance

        response = api_client.get(url)

        assert response.status_code == status.HTTP_302_FOUND
        assert response.url == FAILED_URL

        pending_tx.refresh_from_db()
        assert pending_tx.status == "failed"

        wallet = pending_tx.wallet
        wallet.refresh_from_db()
        assert wallet.total_balance == initial_balance

    def test_verify_deposit_gateway_verification_fails(
        self, api_client, pending_tx, mock_zibal_service
    ):
        """
        GIVEN a pending transaction
        WHEN the gateway verification fails
        THEN the transaction should be marked 'failed'.
        """
        mock_zibal_service.return_value.verify_payment.return_value = {
            "result": 102,
            "message": "Verification failed",
        }
        url = f"{reverse('verify_deposit')}?success=1&trackId={pending_tx.authority}&orderId={pending_tx.order_id}"

        response = api_client.get(url)

        assert response.status_code == status.HTTP_302_FOUND
        assert response.url == FAILED_URL
        pending_tx.refresh_from_db()
        assert pending_tx.status == "failed"

    def test_verify_deposit_already_verified_race_condition(
        self, api_client, pending_tx, mock_zibal_service
    ):
        """
        GIVEN a pending transaction where verification returns 'already verified'
        WHEN an inquiry confirms the payment was successful
        THEN the transaction should be marked 'success' and the balance updated.
        """
        mock_zibal_service.return_value.verify_payment.return_value = {"result": 201}
        mock_zibal_service.return_value.inquiry_payment.return_value = {
            "status": 1,
            "refNumber": "inquiry_ref_123",
        }
        url = f"{reverse('verify_deposit')}?success=1&trackId={pending_tx.authority}&orderId={pending_tx.order_id}"
        initial_balance = pending_tx.wallet.total_balance

        response = api_client.get(url)

        assert response.status_code == status.HTTP_302_FOUND
        assert response.url == SUCCESS_URL

        pending_tx.refresh_from_db()
        assert pending_tx.status == "success"
        assert pending_tx.ref_number == "inquiry_ref_123"
        wallet = pending_tx.wallet
        wallet.refresh_from_db()
        assert wallet.total_balance == initial_balance + pending_tx.amount

    def test_verify_deposit_transaction_not_found(self, api_client):
        """
        GIVEN an invalid orderId or trackId
        WHEN the verification URL is called
        THEN it should redirect to the failed URL without processing.
        """
        url = f"{reverse('verify_deposit')}?success=1&trackId=invalid_track&orderId=invalid_order"
        response = api_client.get(url)
        assert response.status_code == status.HTTP_302_FOUND
        assert response.url == FAILED_URL

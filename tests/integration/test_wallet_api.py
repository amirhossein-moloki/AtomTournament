import pytest
from rest_framework import status
from users.models import User
from wallet.models import Wallet


@pytest.fixture
def user_with_wallet(db):
    user = User.objects.create_user(
        username="walletuser", password="password", phone_number="+9876543210"
    )
    # The Wallet is created by a signal, so we retrieve it and update the balance.
    wallet = Wallet.objects.get(user=user)
    wallet.total_balance = 1000
    wallet.withdrawable_balance = 500
    wallet.save()
    return user


@pytest.mark.django_db
class TestWalletAPI:
    def test_get_wallet_balance(self, api_client, user_with_wallet):
        api_client.force_authenticate(user=user_with_wallet)
        response = api_client.get("/api/wallet/wallets/")
        assert response.status_code == status.HTTP_200_OK
        # The response is a list, so we need to access the first element.
        assert response.data[0]["total_balance"] == "1000.00"
        assert response.data[0]["withdrawable_balance"] == "500.00"

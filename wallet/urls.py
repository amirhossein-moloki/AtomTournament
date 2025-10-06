from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DepositAPIView,
    TransactionViewSet,
    VerifyDepositAPIView,
    WalletViewSet,
    WithdrawalAPIView,
)

router = DefaultRouter()
router.register(r"wallets", WalletViewSet, basename="wallet")
router.register(r"transactions", TransactionViewSet, basename="transaction")

urlpatterns = [
    path("", include(router.urls)),
    path("deposit/", DepositAPIView.as_view(), name="deposit"),
    path("verify-deposit/", VerifyDepositAPIView.as_view(), name="verify_deposit"),
    path("withdraw/", WithdrawalAPIView.as_view(), name="withdraw"),
]

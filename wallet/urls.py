from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminWithdrawalRequestViewSet,
    DepositAPIView,
    RefundAPIView,  # Added
    TransactionViewSet,
    VerifyDepositAPIView,
    WalletViewSet,
    WithdrawalRequestAPIView,
    ZibalWalletListView,  # Added
)

router = DefaultRouter()
router.register(r"wallets", WalletViewSet, basename="wallet")
router.register(r"transactions", TransactionViewSet, basename="transaction")
router.register(
    r"admin/withdrawal-requests",
    AdminWithdrawalRequestViewSet,
    basename="admin-withdrawal-request",
)


urlpatterns = [
    path("", include(router.urls)),
    path("deposit/", DepositAPIView.as_view(), name="deposit"),
    path("verify-deposit/", VerifyDepositAPIView.as_view(), name="verify_deposit"),
    path(
        "withdrawal-requests/",
        WithdrawalRequestAPIView.as_view(),
        name="create-withdrawal-request",
    ),
    # New URLs
    path("refund/", RefundAPIView.as_view(), name="refund"),
    path("admin/zibal-wallets/", ZibalWalletListView.as_view(), name="zibal-wallets"),
]

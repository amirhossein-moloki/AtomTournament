from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PaymentViewSet, TransactionViewSet, WalletViewSet

router = DefaultRouter()
router.register(r"wallets", WalletViewSet)
router.register(r"transactions", TransactionViewSet)
router.register(r"payment", PaymentViewSet, basename="payment")

urlpatterns = [
    path("", include(router.urls)),
    path("payment/verify/", PaymentViewSet.as_view({"get": "verify"}), name="payment-verify"),
]

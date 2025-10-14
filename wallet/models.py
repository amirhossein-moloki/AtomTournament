from django.db import models

from users.models import User


class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    total_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    withdrawable_balance = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    token_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    card_number = models.CharField(
        max_length=16, blank=True, null=True, help_text="شماره کارت"
    )
    sheba_number = models.CharField(
        max_length=26, blank=True, null=True, help_text="شماره شبا"
    )

    @property
    def latest_transactions(self):
        return self.transactions.order_by("-timestamp")[:10]

    class Meta:
        app_label = "wallet"


class WithdrawalRequest(models.Model):
    STATUS_CHOICES = (
        ("pending", "در انتظار بررسی"),
        ("approved", "تایید شده"),
        ("rejected", "رد شده"),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="withdrawal_requests")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Withdrawal request by {self.user.username} for {self.amount}"

    class Meta:
        app_label = "wallet"
        ordering = ["-created_at"]


class Transaction(models.Model):
    TRANSACTION_TYPE_CHOICES = (
        ("deposit", "Deposit"),
        ("withdrawal", "Withdrawal"),
        ("entry_fee", "Entry Fee"),
        ("prize", "Prize"),
        ("token_spent", "Token Spent"),
        ("token_earned", "Token Earned"),
    )
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
    )
    wallet = models.ForeignKey(
        Wallet, on_delete=models.CASCADE, related_name="transactions"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=255, blank=True)
    authority = models.CharField(
        max_length=255, unique=True, null=True, blank=True, help_text="Zibal trackId"
    )
    order_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        help_text="Unique order ID for the transaction",
    )
    ref_number = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Zibal reference number after successful payment",
    )
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="pending", db_index=True
    )

    def __str__(self):
        return f"{self.wallet.user.username} - {self.transaction_type} - {self.amount}"

    class Meta:
        app_label = "wallet"
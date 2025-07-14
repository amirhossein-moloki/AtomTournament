from decimal import Decimal
from django.db import transaction
from .models import Wallet, Transaction

class WalletService:
    @staticmethod
    def deposit(user, amount):
        amount = Decimal(amount)
        if amount <= 0:
            raise ValueError("Deposit amount must be positive.")

        with transaction.atomic():
            wallet, created = Wallet.objects.get_or_create(user=user)
            wallet.total_balance += amount
            wallet.withdrawable_balance += amount
            wallet.save()

            Transaction.objects.create(
                wallet=wallet,
                amount=amount,
                transaction_type='deposit'
            )
        return wallet

    @staticmethod
    def withdraw(user, amount):
        amount = Decimal(amount)
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive.")

        with transaction.atomic():
            wallet = Wallet.objects.get(user=user)
            if wallet.withdrawable_balance < amount:
                raise ValueError("Insufficient withdrawable balance.")

            wallet.total_balance -= amount
            wallet.withdrawable_balance -= amount
            wallet.save()

            Transaction.objects.create(
                wallet=wallet,
                amount=amount,
                transaction_type='withdrawal'
            )
        return wallet

    @staticmethod
    def pay_entry_fee(user, amount):
        amount = Decimal(amount)
        if amount <= 0:
            raise ValueError("Entry fee must be positive.")

        with transaction.atomic():
            wallet = Wallet.objects.get(user=user)
            if wallet.total_balance < amount:
                raise ValueError("Insufficient total balance.")

            wallet.total_balance -= amount
            wallet.save()

            Transaction.objects.create(
                wallet=wallet,
                amount=amount,
                transaction_type='entry_fee'
            )
        return wallet

    @staticmethod
    def receive_prize(user, amount):
        amount = Decimal(amount)
        if amount <= 0:
            raise ValueError("Prize amount must be positive.")

        with transaction.atomic():
            wallet, created = Wallet.objects.get_or_create(user=user)
            wallet.total_balance += amount
            wallet.withdrawable_balance += amount
            wallet.save()

            Transaction.objects.create(
                wallet=wallet,
                amount=amount,
                transaction_type='prize'
            )
        return wallet

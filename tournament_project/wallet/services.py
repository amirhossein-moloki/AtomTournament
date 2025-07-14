from .models import Wallet, Transaction

def update_wallet_balance(user, amount, transaction_type):
    """
    Updates the wallet balance for a user and creates a transaction.
    """
    wallet = Wallet.objects.get(user=user)

    if transaction_type == 'deposit':
        wallet.total_balance += amount
    elif transaction_type == 'withdrawal':
        if wallet.withdrawable_balance < amount:
            raise ValueError("Insufficient withdrawable balance.")
        wallet.withdrawable_balance -= amount
        wallet.total_balance -= amount
    elif transaction_type == 'entry_fee':
        if wallet.total_balance < amount:
            raise ValueError("Insufficient total balance.")
        wallet.total_balance -= amount
    elif transaction_type == 'prize':
        wallet.total_balance += amount
        wallet.withdrawable_balance += amount

    wallet.save()

    Transaction.objects.create(
        wallet=wallet,
        amount=amount,
        transaction_type=transaction_type
    )

    return wallet

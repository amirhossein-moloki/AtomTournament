from django.conf import settings
from zarinpal import ZarinPal
from zarinpal.models import RequestInput, VerifyInput


class ZarinpalService:
    def __init__(self):
        # The zarinpal==1.0.0 library does not use a Config object or sandbox mode.
        # Initialization is done directly with the merchant ID.
        self.zarinpal = ZarinPal(merchant_id=settings.ZARINPAL_MERCHANT_ID)

    def create_payment(
        self, amount, description, callback_url, mobile=None, email=None
    ):
        try:
            # The new library uses a `request` method with a Pydantic model.
            request_data = RequestInput(
                amount=amount,
                callback_url=callback_url,
                description=description,
                metadata={"mobile": mobile, "email": email},
            )
            response = self.zarinpal.request(request_data)
            # The new library returns a pydantic model, convert to dict for consistency
            return response.model_dump()
        except Exception as e:
            return {"error": str(e)}

    def verify_payment(self, amount, authority):
        try:
            # The new library uses a `verify` method with a Pydantic model.
            verify_data = VerifyInput(amount=amount, authority=authority)
            response = self.zarinpal.verify(verify_data)
            # The new library returns a pydantic model, convert to dict for consistency
            return response.model_dump()
        except Exception as e:
            return {"error": str(e)}

    def generate_payment_url(self, authority):
        # The new library has a static method for this.
        return self.zarinpal.get_payment_link(authority)


from django.db import transaction
from .models import Wallet, Transaction
from decimal import Decimal

def process_transaction(
    user, amount: Decimal, transaction_type: str, description: str = ""
) -> (Transaction, str):
    """
    Safely processes a transaction by creating a Transaction object and updating
    the user's wallet balance within a single atomic database transaction.

    Args:
        user: The User object for the transaction.
        amount: The amount for the transaction (should be positive).
        transaction_type: One of the choices from Transaction.TRANSACTION_TYPE_CHOICES.
        description: An optional description for the transaction.

    Returns:
        A tuple of (Transaction, None) on success, or (None, "Error message") on failure.
    """
    if amount <= 0:
        return None, "Transaction amount must be positive."

    if transaction_type not in [t[0] for t in Transaction.TRANSACTION_TYPE_CHOICES]:
        return None, f"Invalid transaction type: {transaction_type}"

    try:
        with transaction.atomic():
            # Lock the wallet row to prevent race conditions
            wallet = Wallet.objects.select_for_update().get(user=user)

            is_debit = transaction_type in ["withdrawal", "entry_fee"]

            if is_debit:
                # Check for sufficient funds
                if wallet.withdrawable_balance < amount:
                    return None, "Insufficient withdrawable balance."
                if wallet.total_balance < amount:
                    return None, "Insufficient total balance."

                # Apply debit
                wallet.total_balance -= amount
                wallet.withdrawable_balance -= amount
            else: # Credit
                # Apply credit
                wallet.total_balance += amount
                if transaction_type in ["deposit", "prize"]:
                    wallet.withdrawable_balance += amount

            # Create the transaction record for audit purposes
            new_transaction = Transaction.objects.create(
                wallet=wallet,
                amount=amount,
                transaction_type=transaction_type,
                description=description,
            )

            # Save the updated wallet balance
            wallet.save()

            return new_transaction, None

    except Wallet.DoesNotExist:
        return None, "User wallet not found."
    except Exception as e:
        # Catch any other unexpected errors
        return None, str(e)

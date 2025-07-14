from decimal import Decimal

from api.exceptions import ApplicationError
from django.db import transaction
from tournaments.models import Tournament
from users.models import User

from .models import Transaction, Wallet


def update_wallet_balance(user: User, amount: Decimal, transaction_type: str):
    """
    Updates the wallet balance for a user and creates a transaction.
    """
    with transaction.atomic():
        wallet = Wallet.objects.select_for_update().get(user=user)

        if transaction_type == "deposit":
            wallet.total_balance += amount
        elif transaction_type == "withdrawal":
            if wallet.withdrawable_balance < amount:
                raise ApplicationError("Insufficient withdrawable balance.")
            wallet.withdrawable_balance -= amount
            wallet.total_balance -= amount
        elif transaction_type == "entry_fee":
            if wallet.total_balance < amount:
                raise ApplicationError("Insufficient total balance.")
            wallet.total_balance -= amount
        elif transaction_type == "prize":
            wallet.total_balance += amount
            wallet.withdrawable_balance += amount

        wallet.save()

        Transaction.objects.create(
            wallet=wallet, amount=amount, transaction_type=transaction_type
        )

        return wallet


def pay_entry_fee(user: User, tournament: Tournament):
    """
    Pays the entry fee for a tournament.
    """
    if tournament.is_free:
        return

    if tournament.entry_fee is None:
        raise ApplicationError("This tournament does not have an entry fee.")

    update_wallet_balance(user, tournament.entry_fee, "entry_fee")


def distribute_prize(tournament: Tournament):
    """
    Distributes the prize money to the winner of the tournament.
    """
    if tournament.is_free:
        return

    if tournament.type == "individual":
        winner = tournament.matches.order_by("-round").first().winner_user
        if winner:
            prize_amount = tournament.entry_fee * tournament.participants.count()
            update_wallet_balance(winner, prize_amount, "prize")
    elif tournament.type == "team":
        winner_team = tournament.matches.order_by("-round").first().winner_team
        if winner_team:
            prize_amount = tournament.entry_fee * tournament.teams.count()
            # Distribute the prize among the team members
            members = winner_team.members.all()
            if members.exists():
                prize_per_member = prize_amount / members.count()
                for member in members:
                    update_wallet_balance(member, prize_per_member, "prize")

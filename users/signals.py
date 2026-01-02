from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import shortuuid

from users.models import User, Role
from wallet.models import Transaction, Wallet


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    """
    Handles actions to be taken after a user is saved.
    - For new users: creates a wallet, assigns a default role, and generates a referral code.
    - For all users: invalidates user-related cache.
    """
    if created:
        # Create a wallet for the new user with an initial token balance
        Wallet.objects.create(user=instance, token_balance=1000)

        # Assign default role
        default_role = Role.get_default_role()
        if default_role:
            instance.groups.add(default_role.group)

        # Generate a unique referral code
        instance.referral_code = shortuuid.uuid()
        instance.save(update_fields=['referral_code'])

    # Invalidate user-specific dashboard cache
    cache.delete(f"dashboard:user:{instance.id}")
    # Invalidate top players lists as user changes might affect rankings
    cache.delete("top_players:prize")
    cache.delete("top_players:rank")


@receiver(post_delete, sender=User)
def user_post_delete(sender, instance, **kwargs):
    """
    Invalidates cache when a user is deleted.
    """
    cache.delete(f"dashboard:user:{instance.id}")
    cache.delete("top_players:prize")
    cache.delete("top_players:rank")


@receiver(post_save, sender=Transaction)
@receiver(post_delete, sender=Transaction)
def invalidate_transaction_related_cache(sender, instance, **kwargs):
    """
    Invalidates cache related to transactions, especially prizes.
    """
    # Invalidate dashboard of the user associated with the transaction's wallet
    if instance.wallet and hasattr(instance.wallet, 'user'):
        cache.delete(f"dashboard:user:{instance.wallet.user.id}")

    # If a prize transaction is updated, invalidate top players and total prize money stats
    if instance.transaction_type == Transaction.TransactionType.PRIZE:
        cache.delete("top_players:prize")
        cache.delete("stats:total_prize_money")

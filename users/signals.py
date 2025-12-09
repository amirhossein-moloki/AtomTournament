import shortuuid
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User
from wallet.models import Wallet


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.create(user=instance, token_balance=1000)
        # Generate a unique referral code
        instance.referral_code = shortuuid.uuid()
        instance.save()
        # TODO: Implement role assignment, profile picture optimization, and rank update

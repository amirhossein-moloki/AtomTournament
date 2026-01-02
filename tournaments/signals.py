from django.core.cache import cache
from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from tournaments.models import Tournament, GameImage, Rank, Match, Report
from common.tasks import convert_image_to_avif_task


@receiver(post_save, sender=Tournament)
@receiver(post_delete, sender=Tournament)
def invalidate_tournament_cache_and_convert_image(sender, instance, **kwargs):
    """
    Invalidates the cache for the top tournaments list and triggers
    AVIF conversion for the tournament image if it has changed.
    """
    cache.delete("top_tournaments")

    if instance.image_has_changed:
        if instance.image:
            transaction.on_commit(
                lambda: convert_image_to_avif_task.delay('tournaments', 'Tournament', instance.id, 'image')
            )


@receiver(post_save, sender=GameImage)
def convert_game_image(sender, instance, **kwargs):
    """
    Triggers AVIF conversion for a game's gallery image.
    """
    if instance.image_has_changed and instance.image:
        transaction.on_commit(
            lambda: convert_image_to_avif_task.delay('tournaments', 'GameImage', instance.id, 'image')
        )


@receiver(post_save, sender=Rank)
def convert_rank_image(sender, instance, **kwargs):
    """
    Triggers AVIF conversion for a rank's image.
    """
    if instance.image_has_changed and instance.image:
        transaction.on_commit(
            lambda: convert_image_to_avif_task.delay('tournaments', 'Rank', instance.id, 'image')
        )


@receiver(post_save, sender=Match)
def convert_match_image(sender, instance, **kwargs):
    """
    Triggers AVIF conversion for a match's result proof.
    """
    if instance.image_has_changed and instance.result_proof:
        transaction.on_commit(
            lambda: convert_image_to_avif_task.delay('tournaments', 'Match', instance.id, 'result_proof')
        )


@receiver(post_save, sender=Report)
def convert_report_image(sender, instance, **kwargs):
    """
    Triggers AVIF conversion for a report's evidence image.
    """
    if instance.image_has_changed and instance.evidence:
        transaction.on_commit(
            lambda: convert_image_to_avif_task.delay('tournaments', 'Report', instance.id, 'evidence')
        )

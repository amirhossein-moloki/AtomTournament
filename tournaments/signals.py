# tournaments/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from common.tasks import convert_image_to_avif_task
from .models import Rank, GameImage, TournamentImage, Match, Report


@receiver(post_save, sender=Rank)
def schedule_rank_avif_conversion(sender, instance, created, **kwargs):
    if instance.image:
        convert_image_to_avif_task.delay(
            app_label='tournaments', model_name='Rank', instance_pk=instance.pk, field_name='image'
        )

@receiver(post_save, sender=GameImage)
def schedule_gameimage_avif_conversion(sender, instance, created, **kwargs):
    if instance.image:
        convert_image_to_avif_task.delay(
            app_label='tournaments', model_name='GameImage', instance_pk=instance.pk, field_name='image'
        )

@receiver(post_save, sender=TournamentImage)
def schedule_tournamentimage_avif_conversion(sender, instance, created, **kwargs):
    if instance.image:
        convert_image_to_avif_task.delay(
            app_label='tournaments', model_name='TournamentImage', instance_pk=instance.pk, field_name='image'
        )

@receiver(post_save, sender=Match)
def schedule_match_avif_conversion(sender, instance, created, **kwargs):
    if instance.result_proof:
        convert_image_to_avif_task.delay(
            app_label='tournaments', model_name='Match', instance_pk=instance.pk, field_name='result_proof'
        )

@receiver(post_save, sender=Report)
def schedule_report_avif_conversion(sender, instance, created, **kwargs):
    if instance.evidence:
        convert_image_to_avif_task.delay(
            app_label='tournaments', model_name='Report', instance_pk=instance.pk, field_name='evidence'
        )

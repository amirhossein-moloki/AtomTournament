from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Rank, GameImage, TournamentImage, Match, Report
from common.tasks import convert_image_to_webp_task

@receiver(post_save, sender=Rank)
def schedule_rank_webp_conversion(sender, instance, created, **kwargs):
    if created and instance.image:
        convert_image_to_webp_task.delay(
            app_label='tournaments', model_name='Rank',
            instance_pk=instance.pk, field_name='image'
        )

@receiver(post_save, sender=GameImage)
def schedule_gameimage_webp_conversion(sender, instance, created, **kwargs):
    if created and instance.image:
        convert_image_to_webp_task.delay(
            app_label='tournaments', model_name='GameImage',
            instance_pk=instance.pk, field_name='image'
        )

@receiver(post_save, sender=TournamentImage)
def schedule_tournamentimage_webp_conversion(sender, instance, created, **kwargs):
    if created and instance.image:
        convert_image_to_webp_task.delay(
            app_label='tournaments', model_name='TournamentImage',
            instance_pk=instance.pk, field_name='image'
        )

@receiver(post_save, sender=Match)
def schedule_match_webp_conversion(sender, instance, created, **kwargs):
    if created and instance.result_proof:
        convert_image_to_webp_task.delay(
            app_label='tournaments', model_name='Match',
            instance_pk=instance.pk, field_name='result_proof'
        )

@receiver(post_save, sender=Report)
def schedule_report_webp_conversion(sender, instance, created, **kwargs):
    if created and instance.evidence:
        convert_image_to_webp_task.delay(
            app_label='tournaments', model_name='Report',
            instance_pk=instance.pk, field_name='evidence'
        )

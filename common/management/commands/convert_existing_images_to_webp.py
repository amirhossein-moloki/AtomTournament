import os
from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage
from django.db import transaction
from users.models import User
from blog.models import Media
from tournaments.models import Rank, GameImage, TournamentImage, Match


class Command(BaseCommand):
    help = 'Safely convert all existing images in the project to WebP format.'

    def handle(self, *args, **options):
        self.stdout.write('Starting safe image conversion to WebP for all models...')

        # --- Process User Profile Pictures ---
        self.stdout.write('\nProcessing User profile pictures...')
        users_to_process = User.objects.exclude(profile_picture__isnull=True).exclude(profile_picture='')
        for user in users_to_process.iterator():
            if user.profile_picture and not user.profile_picture.name.endswith('.webp'):
                try:
                    user.profile_picture.save(user.profile_picture.name, user.profile_picture, save=True)
                    self.stdout.write(self.style.SUCCESS(
                        f'Successfully converted profile picture for user: {user.username}'
                    ))
                except Exception as e:
                    self.stderr.write(self.style.ERROR(
                        f'Could not convert profile picture for user {user.username}: {e}'
                    ))

        # --- Process Media Images (Manual Conversion) ---
        self.stdout.write('\nProcessing Media objects...')
        media_images_to_process = Media.objects.filter(type='image').exclude(storage_key__endswith='.webp')
        for media in media_images_to_process.iterator():
            original_storage_key = media.storage_key
            if not default_storage.exists(original_storage_key):
                self.stderr.write(self.style.WARNING(
                    f'File not found for Media {media.pk}: {original_storage_key}'
                ))
                continue
            try:
                with default_storage.open(original_storage_key, 'rb') as original_file:
                    webp_content = convert_image_to_webp(original_file)
                    new_storage_key = os.path.splitext(original_storage_key)[0] + '.webp'
                saved_path = default_storage.save(new_storage_key, webp_content)
                with transaction.atomic():
                    media.storage_key = saved_path
                    media.url = default_storage.url(saved_path)
                    media.mime = 'image/webp'
                    media.save()
                    if saved_path != original_storage_key:
                        default_storage.delete(original_storage_key)
                self.stdout.write(self.style.SUCCESS(
                    f'Converted Media {original_storage_key} to {saved_path}'
                ))
            except Exception as e:
                self.stderr.write(self.style.ERROR(
                    f'Failed to convert Media {media.pk} ({original_storage_key}): {e}'
                ))

        # --- Process Rank Images ---
        self.stdout.write('\nProcessing Rank images...')
        for rank in Rank.objects.exclude(image__isnull=True).exclude(image='').iterator():
            if rank.image and not rank.image.name.endswith('.webp'):
                try:
                    rank.image.save(rank.image.name, rank.image, save=True)
                    self.stdout.write(self.style.SUCCESS(f'Converted image for Rank: {rank.name}'))
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f'Could not convert image for Rank {rank.name}: {e}'))

        # --- Process Game Images ---
        self.stdout.write('\nProcessing Game images...')
        for game_image in GameImage.objects.exclude(image__isnull=True).exclude(image='').iterator():
            if game_image.image and not game_image.image.name.endswith('.webp'):
                try:
                    game_image.image.save(game_image.image.name, game_image.image, save=True)
                    self.stdout.write(self.style.SUCCESS(f'Converted image for Game: {game_image.game.name} ({game_image.image_type})'))
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f'Could not convert image for Game {game_image.game.name}: {e}'))

        # --- Process Tournament Images ---
        self.stdout.write('\nProcessing Tournament images...')
        for tournament_image in TournamentImage.objects.exclude(image__isnull=True).exclude(image='').iterator():
            if tournament_image.image and not tournament_image.image.name.endswith('.webp'):
                try:
                    tournament_image.image.save(tournament_image.image.name, tournament_image.image, save=True)
                    self.stdout.write(self.style.SUCCESS(f'Converted image for TournamentImage: {tournament_image.name}'))
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f'Could not convert image for TournamentImage {tournament_image.name}: {e}'))

        # --- Process Match Result Proofs ---
        self.stdout.write('\nProcessing Match result proofs...')
        for match in Match.objects.exclude(result_proof__isnull=True).exclude(result_proof='').iterator():
            if match.result_proof and not match.result_proof.name.endswith('.webp'):
                try:
                    match.result_proof.save(match.result_proof.name, match.result_proof, save=True)
                    self.stdout.write(self.style.SUCCESS(f'Converted result proof for Match: {match.id}'))
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f'Could not convert proof for Match {match.id}: {e}'))

        self.stdout.write(self.style.SUCCESS('\nFinished all image conversion processes.'))

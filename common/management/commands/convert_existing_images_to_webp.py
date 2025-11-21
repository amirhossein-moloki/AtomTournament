import os
from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage
from django.db import transaction

# Import all models that have image fields
from users.models import User
from blog.models import Media
from tournaments.models import Rank, GameImage, TournamentImage, Match, Report
from teams.models import Team
from rewards.models import Prize
from verification.models import Verification
from chat.models import Attachment as ChatAttachment
from support.models import TicketAttachment


class Command(BaseCommand):
    help = 'Safely convert all existing images in the project to WebP format.'

    def _process_webp_field_model(self, model_class, field_name, model_name_str):
        """Generic handler for models using WebPImageField."""
        self.stdout.write(f'\nProcessing {model_name_str} images...')
        # Build query dynamically to exclude null or empty fields
        filter_kwargs = {
            f'{field_name}__isnull': False,
        }
        exclude_kwargs = {
            f'{field_name}': '',
            f'{field_name}__endswith': '.webp'
        }

        for instance in model_class.objects.filter(**filter_kwargs).exclude(**exclude_kwargs).iterator():
            image_field = getattr(instance, field_name)
            if image_field and image_field.name:
                try:
                    # Re-saving the field triggers the WebPImageField conversion logic
                    image_field.save(image_field.name, image_field, save=True)
                    self.stdout.write(self.style.SUCCESS(
                        f'Successfully converted image for {model_name_str}: {instance.pk}'
                    ))
                except Exception as e:
                    self.stderr.write(self.style.ERROR(
                        f'Could not convert image for {model_name_str} {instance.pk}: {e}'
                    ))

    def handle(self, *args, **options):
        self.stdout.write('Starting safe image conversion to WebP for all models...')

        # --- Models with WebPImageField (automatic conversion on save) ---
        self._process_webp_field_model(User, 'profile_picture', 'User')
        self._process_webp_field_model(Rank, 'image', 'Rank')
        self._process_webp_field_model(GameImage, 'image', 'GameImage')
        self._process_webp_field_model(TournamentImage, 'image', 'TournamentImage')
        self._process_webp_field_model(Match, 'result_proof', 'Match')
        self._process_webp_field_model(Team, 'team_picture', 'Team')
        self._process_webp_field_model(Prize, 'image', 'Prize')
        self._process_webp_field_model(Verification, 'id_card_image', 'Verification ID Card')
        self._process_webp_field_model(Verification, 'selfie_image', 'Verification Selfie')
        self._process_webp_field_model(ChatAttachment, 'file', 'Chat Attachment')
        self._process_webp_field_model(TicketAttachment, 'file', 'Support Ticket Attachment')
        self._process_webp_field_model(Report, 'evidence', 'Report Evidence')

        # --- Process Media Images (Manual Conversion for generic Media model) ---
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
                    # convert_image_to_webp is not available in this scope, assuming it's in common.utils
                    from common.utils.images import convert_image_to_webp
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
                if 'saved_path' in locals() and default_storage.exists(saved_path):
                    default_storage.delete(saved_path)

        self.stdout.write(self.style.SUCCESS('\nFinished all image conversion processes.'))

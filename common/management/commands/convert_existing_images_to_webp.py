import os
from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage
from django.db import transaction
from users.models import User
from blog.models import Media
from common.utils.images import convert_image_to_webp


class Command(BaseCommand):
    help = 'Safely convert existing images to WebP format.'

    def handle(self, *args, **options):
        self.stdout.write('Starting safe image conversion to WebP...')

        # --- Process User Profile Pictures ---
        self.stdout.write('Processing User profile pictures...')
        users_to_process = User.objects.exclude(profile_picture__isnull=True).exclude(profile_picture='')
        for user in users_to_process.iterator():
            try:
                # The WebPImageField handles the conversion logic automatically and safely on save.
                # It saves the new file before the database commit. Django's file field
                # handles the old file cleanup after the transaction is successful.
                if not user.profile_picture.name.endswith('.webp'):
                    # Trigger the field's save method to perform conversion.
                    user.profile_picture.save(user.profile_picture.name, user.profile_picture, save=True)
                    self.stdout.write(self.style.SUCCESS(
                        f'Successfully converted profile picture for user: {user.username}'
                    ))
            except Exception as e:
                self.stderr.write(self.style.ERROR(
                    f'Could not convert profile picture for user {user.username}: {e}'
                ))

        # --- Process Media Images ---
        self.stdout.write('\nProcessing Media objects...')
        media_images_to_process = Media.objects.filter(type='image').exclude(storage_key__endswith='.webp')
        for media in media_images_to_process.iterator():
            original_storage_key = media.storage_key
            if not default_storage.exists(original_storage_key):
                self.stderr.write(self.style.WARNING(
                    f'File not found in storage for Media object {media.pk}: {original_storage_key}'
                ))
                continue

            try:
                # 1. Read the original file from storage
                with default_storage.open(original_storage_key, 'rb') as original_file:
                    # 2. Convert the image to WebP in memory
                    webp_content = convert_image_to_webp(original_file)
                    new_storage_key = os.path.splitext(original_storage_key)[0] + '.webp'

                # 3. Save the new WebP file to storage
                saved_path = default_storage.save(new_storage_key, webp_content)

                # 4. Use a transaction to update the database and delete the old file
                with transaction.atomic():
                    media.storage_key = saved_path
                    media.url = default_storage.url(saved_path)
                    media.mime = 'image/webp'
                    media.save()

                    # 5. Delete the old file ONLY after the new file is saved and DB is updated
                    if saved_path != original_storage_key:
                        default_storage.delete(original_storage_key)

                self.stdout.write(self.style.SUCCESS(
                    f'Successfully converted Media {original_storage_key} to {saved_path}'
                ))

            except Exception as e:
                self.stderr.write(self.style.ERROR(
                    f'Failed to convert Media object {media.pk} ({original_storage_key}): {e}'
                ))
                # If an error occurred before the transaction, the new file might be orphaned.
                # Clean it up if it exists.
                if 'saved_path' in locals() and default_storage.exists(saved_path):
                    default_storage.delete(saved_path)
                    self.stderr.write(self.style.WARNING(f'Cleaned up orphaned file: {saved_path}'))

        self.stdout.write(self.style.SUCCESS('\nFinished image conversion process.'))

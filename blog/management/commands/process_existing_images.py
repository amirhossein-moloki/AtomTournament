from django.core.management.base import BaseCommand
from django.db.models import Q
from blog.models import Media
from blog.tasks import process_media_image

class Command(BaseCommand):
    help = 'Dispatches a Celery task to process all existing images that have not been converted to AVIF.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Finding unoptimized images to process...'))

        # Find all media objects that are images but not yet in AVIF format.
        # We exclude any media that might already have ".avif" in its storage key to be safe.
        images_to_process = Media.objects.filter(
            Q(type='image') & ~Q(mime='image/avif') & ~Q(storage_key__iendswith='.avif')
        )

        count = images_to_process.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS('No images found that need processing.'))
            return

        self.stdout.write(self.style.NOTICE(f'Found {count} images. Dispatching tasks...'))

        for media in images_to_process:
            self.stdout.write(f'  - Queuing task for Media ID: {media.id} ({media.storage_key})')
            process_media_image.delay(media.id)

        self.stdout.write(self.style.SUCCESS(f'\nSuccessfully queued {count} image processing tasks.'))

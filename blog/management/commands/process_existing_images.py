from django.core.management.base import BaseCommand
from django.db.models import Q
from blog.models import Media
from blog.tasks import process_media_image

class Command(BaseCommand):
    help = 'Finds all non-AVIF images and queues them for conversion to AVIF.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Searching for images to process...'))

        images_to_process = Media.objects.filter(
            Q(type='image') & ~Q(mime='image/avif')
        )

        count = images_to_process.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS('No images to process.'))
            return

        self.stdout.write(self.style.NOTICE(f'Found {count} image(s) to process.'))

        for media in images_to_process:
            process_media_image.delay(media.id)
            self.stdout.write(f'Queued task for Media ID: {media.id}')

        self.stdout.write(self.style.SUCCESS(f'Successfully queued {count} task(s).'))

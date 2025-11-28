import random
import requests
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from faker import Faker
from blog.models import Post, Category, Tag, AuthorProfile, Media

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates a specified number of random posts for testing and development.'

    def add_arguments(self, parser):
        parser.add_argument('count', type=int, help='The number of random posts to create.')

    def handle(self, *args, **options):
        count = options['count']
        fake = Faker()

        # Check if any users exist, create one if not
        if not User.objects.exists():
            default_user = User.objects.create_user(
                username='defaultuser',
                password='password',
                email=fake.email()
            )
            # The AuthorProfile is created by a signal, so we get or create it.
            AuthorProfile.objects.get_or_create(
                user=default_user,
                defaults={
                    'display_name': default_user.username,
                    'bio': fake.paragraph(nb_sentences=3)
                }
            )
            self.stdout.write(self.style.SUCCESS('No users found. Created a default user.'))

        # Get authors, categories, and tags
        authors = list(AuthorProfile.objects.all())
        if not authors:
            self.stderr.write(self.style.ERROR("No author profiles found. Create some first."))
            return

        categories = list(Category.objects.all())
        if not categories:
            for i in range(5):
                Category.objects.create(name=f'Category {i}', slug=f'category-{i}')
            categories = list(Category.objects.all())
            self.stdout.write(self.style.SUCCESS('No categories found. Created 5 default categories.'))

        tags = list(Tag.objects.all())
        if not tags:
            for i in range(10):
                Tag.objects.create(name=f'Tag {i}', slug=f'tag-{i}')
            tags = list(Tag.objects.all())
            self.stdout.write(self.style.SUCCESS('No tags found. Created 10 default tags.'))

        for _ in range(count):
            # Create Media instances for cover and OG image
            cover_media = self._create_dummy_media(fake)
            og_image = self._create_dummy_media(fake)

            post = Post.objects.create(
                title=fake.sentence(nb_words=6),
                excerpt=fake.paragraph(nb_sentences=2),
                content=' '.join(fake.paragraphs(nb=5)),
                status=random.choice(['draft', 'published']),
                author=random.choice(authors),
                category=random.choice(categories),
                cover_media=cover_media,
                og_image=og_image,
            )
            post.tags.set(random.sample(tags, k=random.randint(1, 4)))

        self.stdout.write(self.style.SUCCESS(f'Successfully created {count} random posts.'))

    def _create_dummy_media(self, fake):
        """Downloads a placeholder image and creates a Media object."""
        try:
            response = requests.get('https://via.placeholder.com/800x600.png/007bff/FFFFFF?text=Image')
            response.raise_for_status()  # Raise an exception for bad status codes

            file_name = f"{fake.slug()}.png"
            media = Media(
                title=file_name,
                type='image',
                mime='image/png',
            )
            media.storage_key = ContentFile(response.content, name=file_name)
            media.save()
            return media

        except requests.exceptions.RequestException as e:
            self.stderr.write(self.style.ERROR(f"Failed to download image: {e}"))
            return None

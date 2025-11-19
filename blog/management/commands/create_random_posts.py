import random
import requests
from faker import Faker
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.core.files.base import ContentFile

from blog.models import AuthorProfile, Category, Post, Tag, Media

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates a specified number of random posts'

    def add_arguments(self, parser):
        parser.add_argument('count', type=int, nargs='?', default=10, help='Number of posts to create')

    def handle(self, *args, **options):
        count = options['count']
        fake = Faker()

        # Get or create a user
        users = list(User.objects.all())
        if not users:
            self.stdout.write(self.style.WARNING('No users found. Creating a default user.'))
            default_user = User.objects.create_user(username='testuser', password='password')
            users.append(default_user)

        for i in range(count):
            self.stdout.write(f'Creating post {i + 1}/{count}...')

            # 1. Select a random author
            random_user = random.choice(users)
            author_profile, _ = AuthorProfile.objects.get_or_create(
                user=random_user,
                defaults={'display_name': random_user.username}
            )

            # 2. Generate content
            title = fake.sentence(nb_words=6)
            content = '\n\n'.join(fake.paragraphs(nb=10))
            excerpt = fake.paragraph(nb_sentences=3)
            status = random.choice([Post.STATUS_CHOICES[0][0], Post.STATUS_CHOICES[3][0]]) # draft or published

            # 3. Create Category
            category_name = fake.word().capitalize()
            category_slug = slugify(category_name)
            # Ensure slug is unique
            unique_slug = category_slug
            counter = 1
            while Category.objects.filter(slug=unique_slug).exists():
                unique_slug = f'{category_slug}-{counter}'
                counter += 1
            category = Category.objects.create(name=category_name, slug=unique_slug)

            # 4. Create Tags
            tags = []
            for _ in range(random.randint(2, 5)):
                tag_name = fake.word()
                tag_slug = slugify(tag_name)
                # Ensure slug is unique
                unique_tag_slug = tag_slug
                counter = 1
                while Tag.objects.filter(slug=unique_tag_slug).exists():
                    unique_tag_slug = f'{tag_slug}-{counter}'
                    counter += 1
                tag, _ = Tag.objects.get_or_create(name=tag_name, slug=unique_tag_slug)
                tags.append(tag)

            # 5. Handle Images
            def create_media_from_placeholder(width, height):
                try:
                    url = f'https://via.placeholder.com/{width}x{height}.png'
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()

                    media = Media.objects.create(
                        storage_key=f'placeholders/{fake.uuid4()}.png',
                        url=url,
                        type='image',
                        mime='image/png',
                        width=width,
                        height=height,
                        size_bytes=len(response.content),
                        alt_text=fake.sentence(),
                        title=fake.sentence(nb_words=4),
                        uploaded_by=random_user
                    )
                    return media
                except requests.RequestException as e:
                    self.stdout.write(self.style.ERROR(f'Failed to download image: {e}'))
                    return None

            cover_image = create_media_from_placeholder(1200, 800)
            og_image = create_media_from_placeholder(800, 600)

            # 6. Create Post
            post = Post.objects.create(
                title=title,
                content=content,
                excerpt=excerpt,
                author=author_profile,
                category=category,
                status=status,
                cover_media=cover_image,
                og_image=og_image,
            )
            post.tags.set(tags)
            post.save() # Trigger slug generation and reading time calculation

        self.stdout.write(self.style.SUCCESS(f'Successfully created {count} random posts.'))

from io import StringIO
from unittest.mock import patch, MagicMock
from django.core.management import call_command
from django.test import TestCase
from django.contrib.auth import get_user_model

from blog.models import Post, Category, Tag, AuthorProfile, Media

User = get_user_model()

class CreateRandomPostsTest(TestCase):

    def setUp(self):
        # Create a mock for requests.get that will be used in all tests
        self.patcher = patch('blog.management.commands.create_random_posts.requests.get')
        self.mock_get = self.patcher.start()

        # Configure the mock to return a successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'fake-image-content'
        mock_response.raise_for_status.return_value = None
        self.mock_get.return_value = mock_response

    def tearDown(self):
        # Stop the patcher to clean up
        self.patcher.stop()

    def test_command_creates_posts(self):
        """Test that the command creates the specified number of posts."""
        out = StringIO()
        call_command('create_random_posts', '5', stdout=out)

        self.assertEqual(Post.objects.count(), 5, "Should create 5 posts")
        self.assertIn('Successfully created 5 random posts.', out.getvalue())
        self.assertEqual(self.mock_get.call_count, 10, "Should call requests.get 10 times (2 images per post)")
        self.assertEqual(Media.objects.count(), 10, "Should create 10 media objects")

        # Verify post content
        for post in Post.objects.all():
            self.assertTrue(post.title)
            self.assertTrue(post.content)
            self.assertTrue(post.excerpt)
            self.assertIsNotNone(post.author)
            self.assertIsNotNone(post.category)
            self.assertTrue(post.tags.exists())
            self.assertIn(post.status, ['draft', 'published'])
            self.assertIsNotNone(post.cover_media)
            self.assertIsNotNone(post.og_image)

    def test_command_creates_user_if_none_exist(self):
        """Test that the command creates a default user if no users exist."""
        User.objects.all().delete()
        self.assertEqual(User.objects.count(), 0)

        out = StringIO()
        call_command('create_random_posts', '1', stdout=out)

        self.assertEqual(User.objects.count(), 1, "Should create a default user")
        self.assertEqual(Post.objects.count(), 1, "Should create 1 post")
        self.assertEqual(self.mock_get.call_count, 2, "Should call requests.get 2 times")

    def test_command_uses_existing_users(self):
        """Test that the command uses existing users to create posts."""
        user1 = User.objects.create_user(username='user1', password='password')
        # The AuthorProfile is created by a signal, so we get it instead of creating it.
        author_profile = AuthorProfile.objects.get(user=user1)
        author_profile.display_name = 'User One'
        author_profile.save()

        call_command('create_random_posts', '3')

        self.assertEqual(Post.objects.count(), 3)
        created_posts_authors = [p.author.user for p in Post.objects.all()]
        self.assertIn(user1, created_posts_authors)
        self.assertEqual(self.mock_get.call_count, 6, "Should call requests.get 6 times")

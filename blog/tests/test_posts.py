from django.urls import reverse
from rest_framework import status
from django.utils import timezone
from datetime import timedelta

from blog.factories import PostFactory, CategoryFactory, TagFactory, SeriesFactory, MediaFactory
from blog.models import Post
from blog.tests.base import BaseAPITestCase


class PostAPITest(BaseAPITestCase):
    def test_create_post(self):
        self._authenticate_as_staff()
        category = CategoryFactory()
        tags = TagFactory.create_batch(2)
        url = reverse('blog:post-list-create')
        data = {
            'title': 'New Post',
            'slug': 'new-post',
            'excerpt': 'An excerpt.',
            'content': 'Some content.',
            'status': 'draft',
            'visibility': 'private',
            'author': self.staff_author_profile.pk,
            'category': category.pk,
            'tag_ids': [tag.pk for tag in tags],
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Post.objects.filter(slug='new-post').exists())
        new_post = Post.objects.get(slug='new-post')
        self.assertEqual(new_post.tags.count(), 2)
        self.assertIsNotNone(new_post.reading_time_sec)

    def test_list_posts(self):
        PostFactory.create_batch(3)
        url = reverse('blog:post-list-create')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 3)

    def test_post_pagination(self):
        PostFactory.create_batch(15)
        url = reverse('blog:post-list-create')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 10)
        self.assertIn('next', response.data)
        self.assertIsNotNone(response.data['next'])

    def test_post_filtering(self):
        series = SeriesFactory()
        category = CategoryFactory()
        tag1 = TagFactory()
        tag2 = TagFactory()

        PostFactory(series=series, visibility='private', category=category, tags=[tag1])
        PostFactory.create_batch(2, visibility='public', tags=[tag2])
        url = reverse('blog:post-list-create')

        # Filter by series
        response = self.client.get(url, {'series': series.pk}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

        # Filter by visibility
        response = self.client.get(url, {'visibility': 'public'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

        # Filter by category
        response = self.client.get(url, {'category': category.slug}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

        # Filter by tags
        response = self.client.get(url, {'tags': tag1.slug}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

        response = self.client.get(url, {'tags': tag2.slug}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_post_date_filtering(self):
        PostFactory(published_at=timezone.now() - timedelta(days=5))
        PostFactory(published_at=timezone.now() - timedelta(days=15))
        url = reverse('blog:post-list-create')

        # Filter by published_after
        after_date = (timezone.now() - timedelta(days=10)).isoformat()
        response = self.client.get(url, {'published_after': after_date}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_retrieve_post(self):
        yesterday = timezone.now() - timedelta(days=1)
        cover_media = MediaFactory()
        in_content_media = MediaFactory()

        post_content = f'<p>Some text</p><img src="/media/{in_content_media.storage_key}" />'
        post = PostFactory(
            status='published',
            published_at=yesterday,
            cover_media=cover_media,
            content=post_content
        )
        post.save()  # Trigger the media attachment logic

        url = reverse('blog:post-detail', kwargs={'slug': post.slug})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], post.title)

        # Check for media attachments
        self.assertIn('media_attachments', response.data)
        attachments = response.data['media_attachments']
        self.assertEqual(len(attachments), 2)

        attachment_types = {att['attachment_type'] for att in attachments}
        self.assertIn('cover', attachment_types)
        self.assertIn('in-content', attachment_types)

    def test_update_post(self):
        self._authenticate_as_staff()
        post = PostFactory(author=self.staff_author_profile)
        url = reverse('blog:post-detail', kwargs={'slug': post.slug})
        data = {'title': 'Updated Title'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        post.refresh_from_db()
        self.assertEqual(post.title, 'Updated Title')

    def test_admin_can_update_other_users_post(self):
        """
        Ensures an admin can update a post they do not own.
        """
        self._authenticate_as_staff()
        # self.user is the non-staff user, self.author_profile is their profile
        post = PostFactory(author=self.author_profile)
        url = reverse('blog:post-detail', kwargs={'slug': post.slug})
        data = {'title': 'Admin Edited Title'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        post.refresh_from_db()
        self.assertEqual(post.title, 'Admin Edited Title')

    def test_delete_post(self):
        self._authenticate_as_staff()
        post = PostFactory(author=self.staff_author_profile)
        url = reverse('blog:post-detail', kwargs={'slug': post.slug})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Post.objects.filter(pk=post.pk).exists())

    def test_unique_slug_generation(self):
        self._authenticate_as_staff()
        post1 = PostFactory(title='My test post', author=self.staff_author_profile)
        post2 = PostFactory(title='My test post', author=self.staff_author_profile)
        self.assertNotEqual(post1.slug, post2.slug)

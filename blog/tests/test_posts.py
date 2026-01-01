from django.urls import reverse
from rest_framework import status
from django.utils import timezone
from datetime import timedelta

from jalali_date import datetime2jalali

from django.db.models.signals import post_save
from blog.factories import (
    PostFactory, CategoryFactory, TagFactory, SeriesFactory, MediaFactory, UserFactory
)
from blog.models import Post, AuthorProfile
from blog.tests.base import BaseAPITestCase


class PostPermissionAPITest(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('blog:post-list')
        self.post_data = {
            'title': 'Test Post by Author',
            'slug': 'test-post-by-author',
            'excerpt': 'An excerpt.',
            'content': 'Some content.',
        }

    def test_guest_user_can_list_posts(self):
        PostFactory.create_batch(3)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 3)

    def test_guest_user_cannot_create_post(self):
        response = self.client.post(self.url, self.post_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_without_author_profile_cannot_create_post(self):
        # Create a new user that doesn't have an author profile
        regular_user = UserFactory()
        AuthorProfile.objects.filter(user=regular_user).delete() # Ensure no profile exists
        self._authenticate(regular_user)
        response = self.client.post(self.url, self.post_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_author_user_can_create_post(self):
        # self.user from BaseAPITestCase needs an author profile explicitly created
        AuthorProfile.objects.get_or_create(user=self.user, display_name=self.user.username)
        self._authenticate(self.user)
        response = self.client.post(self.url, self.post_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Post.objects.filter(slug=self.post_data['slug']).exists())

    def test_staff_user_can_create_post(self):
        self._authenticate_as_staff()
        post_data = self.post_data.copy()
        post_data['title'] = 'Test Post by Staff'
        post_data['slug'] = 'test-post-by-staff'
        response = self.client.post(self.url, post_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Post.objects.filter(slug=post_data['slug']).exists())


class PostAPITest(BaseAPITestCase):
    def test_create_post(self):
        self._authenticate_as_staff()
        category = CategoryFactory()
        tags = TagFactory.create_batch(2)
        url = reverse('blog:post-list')
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
        url = reverse('blog:post-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 3)

    def test_default_ordering_is_latest_first(self):
        older_post = PostFactory(published_at=timezone.now() - timedelta(days=3))
        newest_post = PostFactory(published_at=timezone.now())
        middle_post = PostFactory(published_at=timezone.now() - timedelta(days=1))

        url = reverse('blog:post-list')
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = [post['id'] for post in response.data['results']]
        self.assertEqual(returned_ids[:3], [newest_post.id, middle_post.id, older_post.id])


    def test_post_pagination(self):
        PostFactory.create_batch(15)
        url = reverse('blog:post-list')
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
        url = reverse('blog:post-list')

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

    def test_post_is_hot_filtering(self):
        # Hot post: recent, high views
        PostFactory(
            published_at=timezone.now() - timedelta(days=15),
            views_count=2000
        )
        # Not hot post: old
        PostFactory(
            published_at=timezone.now() - timedelta(days=45),
            views_count=2000
        )
        # Not hot post: low views
        PostFactory(
            published_at=timezone.now() - timedelta(days=15),
            views_count=500
        )
        url = reverse('blog:post-list')

        # Filter by is_hot=True
        response = self.client.get(url, {'is_hot': 'true'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

        # Filter by is_hot=False
        response = self.client.get(url, {'is_hot': 'false'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_post_date_filtering(self):
        PostFactory(published_at=timezone.now() - timedelta(days=5))
        PostFactory(published_at=timezone.now() - timedelta(days=15))
        url = reverse('blog:post-list')

        # Filter by published_after
        after_date = (timezone.now() - timedelta(days=10)).isoformat()
        response = self.client.get(url, {'published_after': after_date}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)



    def test_slug_endpoint_returns_id_and_author_avatar(self):
        author_profile = self.author_profile
        author_profile.avatar = MediaFactory()
        author_profile.save()

        post = PostFactory(status='published', author=author_profile)

        url = reverse('blog:post-by-slug', kwargs={'slug': post.slug})
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], post.id)
        self.assertIn('author', response.data)
        self.assertEqual(response.data['author']['display_name'], author_profile.display_name)
        self.assertIsNotNone(response.data['author']['avatar'])

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

    def test_related_posts_pagination(self):
        tag = TagFactory()
        post = PostFactory(tags=[tag])
        PostFactory.create_batch(15, tags=[tag])
        url = reverse('blog:post-related', kwargs={'slug': post.slug})
        response = self.client.get(url, {'page_size': 5})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 5)
        self.assertIn('next', response.data)

    def test_same_category_posts_pagination(self):
        category = CategoryFactory()
        post = PostFactory(category=category)
        PostFactory.create_batch(15, category=category)
        url = reverse('blog:post-same-category', kwargs={'slug': post.slug})
        response = self.client.get(url, {'page_size': 7})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 7)
        self.assertIn('next', response.data)

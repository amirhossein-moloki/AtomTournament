from django.urls import reverse
from rest_framework import status
from django.utils import timezone
from datetime import timedelta

from blog.factories import PostFactory, CategoryFactory, TagFactory
from blog.models import Post
from blog.tests.base import BaseAPITestCase


class PostAPITest(BaseAPITestCase):
    def test_create_post(self):
        self._authenticate_as_staff()
        category = CategoryFactory()
        tags = TagFactory.create_batch(2)
        url = reverse('post-list-create')
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
        url = reverse('post-list-create')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_retrieve_post(self):
        yesterday = timezone.now() - timedelta(days=1)
        post = PostFactory(status='published', published_at=yesterday)
        url = reverse('post-detail', kwargs={'slug': post.slug})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], post.title)

    def test_update_post(self):
        self._authenticate_as_staff()
        post = PostFactory(author=self.staff_author_profile)
        url = reverse('post-detail', kwargs={'slug': post.slug})
        data = {'title': 'Updated Title'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        post.refresh_from_db()
        self.assertEqual(post.title, 'Updated Title')

    def test_delete_post(self):
        self._authenticate_as_staff()
        post = PostFactory(author=self.staff_author_profile)
        url = reverse('post-detail', kwargs={'slug': post.slug})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Post.objects.filter(pk=post.pk).exists())

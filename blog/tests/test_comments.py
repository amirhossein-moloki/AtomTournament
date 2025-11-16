from unittest.mock import patch

from django.urls import reverse
from rest_framework import status

from blog.factories import PostFactory, CommentFactory
from blog.models import Comment
from blog.tests.base import BaseAPITestCase


class CommentAPITest(BaseAPITestCase):
    @patch('blog.views.notify_author_on_new_comment.delay')
    def test_create_comment(self, mock_task):
        self._authenticate()
        post = PostFactory()
        url = reverse('comment-list')
        data = {
            'post': post.pk,
            'author_name': 'Test User',
            'author_email': 'test@example.com',
            'content': 'A test comment.',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Comment.objects.filter(post=post, content='A test comment.').exists())
        new_comment = Comment.objects.latest('id')
        mock_task.assert_called_once_with(new_comment.id)

    @patch('blog.views.notify_author_on_new_comment.delay')
    def test_create_nested_comment(self, mock_task):
        self._authenticate()
        parent_comment = CommentFactory()
        url = reverse('comment-list')
        data = {
            'post': parent_comment.post.pk,
            'parent': parent_comment.pk,
            'author_name': 'Reply User',
            'author_email': 'reply@example.com',
            'content': 'A reply to the comment.',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Comment.objects.filter(parent=parent_comment).exists())

    def test_list_comments_for_post(self):
        self._authenticate()
        post = PostFactory()
        CommentFactory.create_batch(3, post=post)
        url = reverse('comment-list') + f'?post={post.pk}'
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

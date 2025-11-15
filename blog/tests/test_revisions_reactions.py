from django.urls import reverse
from rest_framework import status

from blog.factories import RevisionFactory, ReactionFactory, PostFactory, CommentFactory
from blog.tests.base import BaseAPITestCase


class RevisionAPITest(BaseAPITestCase):
    def test_list_revisions_for_post(self):
        post = PostFactory()
        RevisionFactory.create_batch(3, post=post)
        url = reverse('revision-list') + f'?post={post.pk}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)


class ReactionAPITest(BaseAPITestCase):
    def test_create_reaction_for_post(self):
        self._authenticate()
        post = PostFactory()
        url = reverse('reaction-list')
        data = {
            'target_type': 'post',
            'target_id': post.pk,
            'reaction': 'like',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_reaction_for_comment(self):
        self._authenticate()
        comment = CommentFactory()
        url = reverse('reaction-list')
        data = {
            'target_type': 'comment',
            'target_id': comment.pk,
            'reaction': 'thumbs_up',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

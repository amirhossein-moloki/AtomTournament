from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from blog.models import Post, Comment, Reaction
from blog.factories import PostFactory, UserFactory, CommentFactory


class ReactionAPITests(APITestCase):
    def setUp(self):
        self.user = UserFactory()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.post = PostFactory()
        self.comment = CommentFactory(post=self.post, user=self.user)

    def test_react_to_post(self):
        url = reverse('blog:post-react', kwargs={'slug': self.post.slug})
        data = {'reaction': 'like'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Reaction.objects.count(), 1)
        self.assertEqual(Reaction.objects.first().reaction, 'like')

    def test_react_to_post_twice_removes_reaction(self):
        url = reverse('blog:post-react', kwargs={'slug': self.post.slug})
        data = {'reaction': 'like'}
        self.client.post(url, data, format='json')
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Reaction.objects.count(), 0)

    def test_get_post_reactions(self):
        Reaction.objects.create(user=self.user, content_object=self.post, reaction='like')
        url = reverse('blog:post-reactions', kwargs={'slug': self.post.slug})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_react_to_comment(self):
        url = reverse('blog:comment-react', kwargs={'pk': self.comment.pk})
        data = {'reaction': 'heart'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Reaction.objects.count(), 1)
        self.assertEqual(Reaction.objects.first().reaction, 'heart')

    def test_react_to_comment_twice_removes_reaction(self):
        url = reverse('blog:comment-react', kwargs={'pk': self.comment.pk})
        data = {'reaction': 'heart'}
        self.client.post(url, data, format='json')
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Reaction.objects.count(), 0)

    def test_get_comment_reactions(self):
        Reaction.objects.create(user=self.user, content_object=self.comment, reaction='heart')
        url = reverse('blog:comment-reactions', kwargs={'pk': self.comment.pk})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

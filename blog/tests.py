from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from users.models import User
from .models import Post, Tag, Category, AuthorProfile


class BlogAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="password", phone_number="+12125552368"
        )
        self.author_profile = AuthorProfile.objects.create(
            user=self.user, display_name="Test User"
        )
        self.category = Category.objects.create(name="Test Category", slug="test-category")
        self.tag = Tag.objects.create(name="Test Tag", slug="test-tag")
        self.published_post = Post.objects.create(
            title="Published Post",
            slug="published-post",
            author=self.author_profile,
            content="This is a published post.",
            status="published",
            category=self.category,
        )
        self.published_post.tags.add(self.tag)
        self.draft_post = Post.objects.create(
            title="Draft Post",
            slug="draft-post",
            author=self.author_profile,
            content="This is a draft post.",
            status="draft",
        )

    def test_list_published_posts_unauthenticated(self):
        """
        Ensure unauthenticated users can only see published posts.
        """
        url = reverse("post-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Assuming draft posts are not shown to unauthenticated users
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], self.published_post.title)

    def test_list_posts_authenticated_author(self):
        """
        Ensure authenticated authors can see their own draft and published posts.
        """
        self.client.force_authenticate(user=self.user)
        url = reverse("post-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_create_post_authenticated(self):
        """
        Ensure authenticated users can create a new post.
        """
        self.client.force_authenticate(user=self.user)
        url = reverse("post-list")
        data = {
            "title": "A New Post",
            "slug": "a-new-post",
            "content": "This is the content of the new post.",
            "status": "published",
            "category": self.category.id,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Post.objects.count(), 3)

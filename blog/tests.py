from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from users.models import User
from .models import Post, Tag, Category, Comment


class BlogAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="password", phone_number="+12125552368"
        )
        self.other_user = User.objects.create_user(
            username="otheruser", password="password", phone_number="+12125552369"
        )
        self.category = Category.objects.create(name="Test Category")
        self.tag = Tag.objects.create(name="Test Tag")
        self.published_post = Post.objects.create(
            title="Published Post",
            slug="published-post",
            author=self.user,
            content="This is a published post.",
            status="published",
            category=self.category,
        )
        self.published_post.tags.add(self.tag)
        self.draft_post = Post.objects.create(
            title="Draft Post",
            slug="draft-post",
            author=self.user,
            content="This is a draft post.",
            status="draft",
        )

    def test_list_posts(self):
        url = reverse("post-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], self.published_post.title)

    def test_retrieve_post(self):
        url = reverse("post-detail", kwargs={"slug": self.published_post.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], self.published_post.title)

    def test_create_post(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("post-list")
        data = {
            "title": "New Post",
            "content": "Some content",
            "category": self.category.id,
            "tags": [self.tag.id],
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Post.objects.count(), 3)

    def test_update_post_by_author(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("post-detail", kwargs={"slug": self.published_post.slug})
        data = {"title": "Updated Title", "category": self.category.id}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Updated Title")

    def test_update_post_by_other_user(self):
        self.client.force_authenticate(user=self.other_user)
        url = reverse("post-detail", kwargs={"slug": self.published_post.slug})
        data = {"title": "Updated Title"}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_post_by_author(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("post-detail", kwargs={"slug": self.published_post.slug})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Post.objects.count(), 1)

    def test_delete_post_by_other_user(self):
        self.client.force_authenticate(user=self.other_user)
        url = reverse("post-detail", kwargs={"slug": self.published_post.slug})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_tags(self):
        url = reverse("tag-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_list_categories(self):
        url = reverse("category-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_comment(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("post-comments-list", kwargs={"post_slug": self.published_post.slug})
        data = {"content": "A new comment"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Comment.objects.count(), 1)

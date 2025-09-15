from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from users.models import User
from .models import Post, Tag, Category, Comment
from PIL import Image
import io


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
        # For related posts test
        self.tag2 = Tag.objects.create(name="Test Tag 2")
        self.related_post = Post.objects.create(
            title="Related Post",
            slug="related-post",
            author=self.user,
            content="This is a related post.",
            status="published",
        )
        self.related_post.tags.add(self.tag)
        self.related_post.tags.add(self.tag2)

    def test_list_posts(self):
        url = reverse("post-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

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
        self.assertEqual(Post.objects.count(), 4)

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
        self.assertEqual(Post.objects.count(), 2)

    def test_delete_post_by_other_user(self):
        self.client.force_authenticate(user=self.other_user)
        url = reverse("post-detail", kwargs={"slug": self.published_post.slug})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_tags(self):
        url = reverse("tag-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

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

    def test_create_post_with_image(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("post-list")
        image = io.BytesIO()
        Image.new("RGB", (100, 100)).save(image, "jpeg")
        image.seek(0)
        image_file = SimpleUploadedFile("test.jpg", image.read(), content_type="image/jpeg")
        data = {
            "title": "New Post with Image",
            "content": "Some content",
            "category": self.category.id,
            "tags": [self.tag.id],
            "featured_image": image_file,
        }
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Post.objects.count(), 4)
        self.assertIn("featured_image", response.data)

    def test_related_posts(self):
        url = reverse("post-detail", kwargs={"slug": self.published_post.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("related_posts", response.data)
        self.assertEqual(len(response.data["related_posts"]), 1)
        self.assertEqual(
            response.data["related_posts"][0]["title"], self.related_post.title
        )

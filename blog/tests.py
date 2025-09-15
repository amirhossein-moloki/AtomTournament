from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from users.models import User
from datetime import timedelta
from django.utils import timezone
from .models import Post, Tag, Category, Comment, CommentReaction, CommentReport
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

    def test_create_reply_to_comment(self):
        self.client.force_authenticate(user=self.user)
        comment = Comment.objects.create(
            post=self.published_post, author=self.user, content="Original comment"
        )
        url = reverse("post-comments-list", kwargs={"post_slug": self.published_post.slug})
        data = {"content": "A reply", "parent": comment.id}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Comment.objects.count(), 2)
        reply = Comment.objects.get(id=response.data["id"])
        self.assertEqual(reply.parent, comment)

    def test_react_to_comment_add(self):
        self.client.force_authenticate(user=self.user)
        comment = Comment.objects.create(
            post=self.published_post, author=self.other_user, content="A comment to react to"
        )
        url = reverse("post-comments-react", kwargs={"post_slug": self.published_post.slug, "pk": comment.pk})
        data = {"reaction_type": "like"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(comment.reactions.count(), 1)
        self.assertEqual(response.data["user_reaction"], "like")

    def test_react_to_comment_remove(self):
        self.client.force_authenticate(user=self.user)
        comment = Comment.objects.create(
            post=self.published_post, author=self.other_user, content="A comment to un-react to"
        )
        CommentReaction.objects.create(comment=comment, user=self.user, reaction_type="like")
        self.assertEqual(comment.reactions.count(), 1)
        url = reverse("post-comments-react", kwargs={"post_slug": self.published_post.slug, "pk": comment.pk})
        data = {"reaction_type": "like"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(comment.reactions.count(), 0)

    def test_react_to_comment_change(self):
        self.client.force_authenticate(user=self.user)
        comment = Comment.objects.create(
            post=self.published_post, author=self.other_user, content="A comment to change reaction"
        )
        CommentReaction.objects.create(comment=comment, user=self.user, reaction_type="like")
        self.assertEqual(comment.reactions.count(), 1)
        url = reverse("post-comments-react", kwargs={"post_slug": self.published_post.slug, "pk": comment.pk})
        data = {"reaction_type": "love"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(comment.reactions.count(), 1)
        self.assertEqual(response.data["user_reaction"], "love")

    def test_react_to_comment_invalid_type(self):
        self.client.force_authenticate(user=self.user)
        comment = Comment.objects.create(
            post=self.published_post, author=self.other_user, content="A comment"
        )
        url = reverse("post-comments-react", kwargs={"post_slug": self.published_post.slug, "pk": comment.pk})
        data = {"reaction_type": "invalid"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_comment_by_author(self):
        self.client.force_authenticate(user=self.user)
        comment = Comment.objects.create(
            post=self.published_post, author=self.user, content="A comment to delete"
        )
        url = reverse("post-comments-detail", kwargs={"post_slug": self.published_post.slug, "pk": comment.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Comment.objects.count(), 0)

    def test_delete_comment_by_other_user(self):
        self.client.force_authenticate(user=self.other_user)
        comment = Comment.objects.create(
            post=self.published_post, author=self.user, content="A comment to delete"
        )
        url = reverse("post-comments-detail", kwargs={"post_slug": self.published_post.slug, "pk": comment.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_edit_comment_by_author_within_time_limit(self):
        self.client.force_authenticate(user=self.user)
        comment = Comment.objects.create(
            post=self.published_post, author=self.user, content="Original content"
        )
        url = reverse("post-comments-detail", kwargs={"post_slug": self.published_post.slug, "pk": comment.pk})
        data = {"content": "Updated content"}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["content"], "Updated content")

    def test_edit_comment_by_author_outside_time_limit(self):
        self.client.force_authenticate(user=self.user)
        comment = Comment.objects.create(
            post=self.published_post, author=self.user, content="Original content"
        )
        # Manually set the creation time to be in the past
        comment.created_at = timezone.now() - timedelta(minutes=15)
        comment.save()
        url = reverse("post-comments-detail", kwargs={"post_slug": self.published_post.slug, "pk": comment.pk})
        data = {"content": "Updated content"}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_report_comment(self):
        self.client.force_authenticate(user=self.user)
        comment = Comment.objects.create(
            post=self.published_post, author=self.other_user, content="Inappropriate content"
        )
        url = reverse("post-comments-report", kwargs={"post_slug": self.published_post.slug, "pk": comment.pk})
        data = {"reason": "This is spam."}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CommentReport.objects.count(), 1)
        self.assertEqual(CommentReport.objects.first().reason, "This is spam.")

    def test_report_own_comment(self):
        self.client.force_authenticate(user=self.user)
        comment = Comment.objects.create(
            post=self.published_post, author=self.user, content="My own comment"
        )
        url = reverse("post-comments-report", kwargs={"post_slug": self.published_post.slug, "pk": comment.pk})
        data = {"reason": "I want to report myself."}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_report_comment(self):
        self.client.force_authenticate(user=self.user)
        comment = Comment.objects.create(
            post=self.published_post, author=self.other_user, content="Inappropriate content"
        )
        # First report
        CommentReport.objects.create(comment=comment, reporter=self.user, reason="First report")
        # Second report
        url = reverse("post-comments-report", kwargs={"post_slug": self.published_post.slug, "pk": comment.pk})
        data = {"reason": "Second report"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_sort_comments_by_newest(self):
        comment1 = Comment.objects.create(
            post=self.published_post, author=self.user, content="First comment"
        )
        comment1.created_at = timezone.now() - timedelta(days=1)
        comment1.save()
        comment2 = Comment.objects.create(
            post=self.published_post, author=self.user, content="Second comment"
        )
        url = reverse("post-comments-list", kwargs={"post_slug": self.published_post.slug})
        response = self.client.get(url, {"ordering": "-created_at"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["id"], comment2.id)
        self.assertEqual(response.data[1]["id"], comment1.id)

    def test_sort_comments_by_most_popular(self):
        comment1 = Comment.objects.create(
            post=self.published_post, author=self.user, content="Less popular"
        )
        comment2 = Comment.objects.create(
            post=self.published_post, author=self.user, content="Most popular"
        )
        # React to comment 2 to make it more popular
        CommentReaction.objects.create(comment=comment2, user=self.user, reaction_type="like")
        CommentReaction.objects.create(comment=comment2, user=self.other_user, reaction_type="love")
        # React to comment 1
        CommentReaction.objects.create(comment=comment1, user=self.other_user, reaction_type="like")

        url = reverse("post-comments-list", kwargs={"post_slug": self.published_post.slug})
        response = self.client.get(url, {"ordering": "-reactions_count"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["id"], comment2.id)
        self.assertEqual(response.data[1]["id"], comment1.id)

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

from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name=_("Name"))
    slug = models.SlugField(max_length=50, unique=True, blank=True)

    class Meta:
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Name"))
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Post(models.Model):
    STATUS_CHOICES = (
        ("draft", _("Draft")),
        ("published", _("Published")),
    )

    title = models.CharField(max_length=200, verbose_name=_("Title"))
    slug = models.SlugField(max_length=200, unique_for_date="created_at", verbose_name=_("Slug"), blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blog_posts",
        verbose_name=_("Author"),
    )
    content = models.TextField(verbose_name=_("Content"))
    featured_image = models.ImageField(
        upload_to="blog/featured_images/", null=True, blank=True, verbose_name=_("Featured Image")
    )
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="draft", verbose_name=_("Status")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts",
        verbose_name=_("Category"),
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="posts", verbose_name=_("Tags"))

    class Meta:
        ordering = ("-created_at",)
        verbose_name = _("Post")
        verbose_name_plural = _("Posts")

    def __str__(self):
        return self.title


class Comment(models.Model):
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name="comments", verbose_name=_("Post")
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name=_("Author"),
    )
    content = models.TextField(verbose_name=_("Content"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="replies",
        verbose_name=_("Parent"),
    )
    reactions = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="CommentReaction",
        related_name="reacted_comments",
        blank=True,
        verbose_name=_("Reactions"),
    )
    active = models.BooleanField(default=True, verbose_name=_("Active"))

    class Meta:
        ordering = ("created_at",)
        verbose_name = _("Comment")
        verbose_name_plural = _("Comments")

    def __str__(self):
        return f"Comment by {self.author} on {self.post}"


class CommentReaction(models.Model):
    class ReactionType(models.TextChoices):
        LIKE = "like", _("Like")
        LOVE = "love", _("Love")
        HAHA = "haha", _("Haha")
        WOW = "wow", _("Wow")
        SAD = "sad", _("Sad")
        ANGRY = "angry", _("Angry")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_("User")
    )
    comment = models.ForeignKey(
        Comment, on_delete=models.CASCADE, verbose_name=_("Comment")
    )
    reaction_type = models.CharField(
        max_length=10,
        choices=ReactionType.choices,
        default=ReactionType.LIKE,
        verbose_name=_("Reaction Type"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "comment"], name="unique_user_comment_reaction"
            )
        ]
        verbose_name = _("Comment Reaction")
        verbose_name_plural = _("Comment Reactions")

    def __str__(self):
        return f"{self.user} reacted to {self.comment} with {self.get_reaction_type_display()}"


class CommentReport(models.Model):
    class ReportStatus(models.TextChoices):
        PENDING = "pending", _("Pending")
        RESOLVED = "resolved", _("Resolved")
        DISMISSED = "dismissed", _("Dismissed")

    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name="reports",
        verbose_name=_("Comment"),
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comment_reports",
        verbose_name=_("Reporter"),
    )
    reason = models.TextField(verbose_name=_("Reason"))
    status = models.CharField(
        max_length=10,
        choices=ReportStatus.choices,
        default=ReportStatus.PENDING,
        verbose_name=_("Status"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["comment", "reporter"], name="unique_comment_reporter"
            )
        ]
        verbose_name = _("Comment Report")
        verbose_name_plural = _("Comment Reports")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Report by {self.reporter} on comment {self.comment.id}"

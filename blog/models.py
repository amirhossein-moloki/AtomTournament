from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords


class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField("Permission", blank=True, related_name="roles")

    def __str__(self):
        return self.name


class Permission(models.Model):
    code = models.CharField(max_length=100, unique=True, help_text=_("e.g., post.create, post.publish"))
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.code


class AuthorProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="author_profile"
    )
    display_name = models.CharField(max_length=100)
    bio = models.TextField(blank=True)
    avatar = models.ForeignKey(
        "Media", on_delete=models.SET_NULL, null=True, blank=True, related_name="author_avatars"
    )
    social_links = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.display_name


class Media(models.Model):
    TYPE_CHOICES = (
        ("image", _("Image")),
        ("video", _("Video")),
        ("audio", _("Audio")),
        ("file", _("File")),
    )

    storage_key = models.CharField(max_length=255, unique=True)
    url = models.URLField(max_length=512)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    mime = models.CharField(max_length=100)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    duration = models.PositiveIntegerField(null=True, blank=True, help_text=_("In seconds"))
    size_bytes = models.PositiveBigIntegerField()
    alt_text = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="uploaded_media"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or self.storage_key


class Series(models.Model):
    ORDER_STRATEGY_CHOICES = (
        ("manual", _("Manual")),
        ("by_date", _("By Date")),
    )

    slug = models.SlugField(max_length=200, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order_strategy = models.CharField(
        max_length=10, choices=ORDER_STRATEGY_CHOICES, default="manual"
    )

    def __str__(self):
        return self.title


class Page(models.Model):
    STATUS_CHOICES = (
        ("draft", _("Draft")),
        ("published", _("Published")),
    )

    slug = models.SlugField(max_length=200, unique=True)
    title = models.CharField(max_length=200)
    content = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    published_at = models.DateTimeField(null=True, blank=True)
    seo_title = models.CharField(max_length=255, blank=True)
    seo_description = models.CharField(max_length=500, blank=True)

    def __str__(self):
        return self.title


class Menu(models.Model):
    LOCATION_CHOICES = (
        ("header", _("Header")),
        ("footer", _("Footer")),
        ("sidebar", _("Sidebar")),
    )

    name = models.CharField(max_length=100, unique=True)
    location = models.CharField(max_length=20, choices=LOCATION_CHOICES, unique=True, null=True, blank=True)

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name="items")
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    label = models.CharField(max_length=100)
    url = models.CharField(max_length=500)
    order = models.PositiveIntegerField()
    target_blank = models.BooleanField(default=False)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.label


class Revision(models.Model):
    post = models.ForeignKey("Post", on_delete=models.CASCADE, related_name="revisions")
    editor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="edited_revisions"
    )
    title = models.CharField(max_length=200)
    excerpt = models.TextField(blank=True)
    content = models.TextField()
    change_note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Revision for {self.post.title} at {self.created_at}"


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name=_("Name"))
    slug = models.SlugField(max_length=50, unique=True, blank=True)
    description = models.TextField(blank=True, verbose_name=_("Description"))

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
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        verbose_name=_("Parent"),
    )
    description = models.TextField(blank=True, verbose_name=_("Description"))
    order = models.PositiveIntegerField(default=0, verbose_name=_("Order"))

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ["parent__id", "order"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Post(models.Model):
    STATUS_CHOICES = (
        ("draft", _("Draft")),
        ("review", _("In Review")),
        ("scheduled", _("Scheduled")),
        ("published", _("Published")),
        ("archived", _("Archived")),
    )
    VISIBILITY_CHOICES = (
        ("public", _("Public")),
        ("private", _("Private")),
        ("unlisted", _("Unlisted")),
    )

    slug = models.SlugField(max_length=200, unique=True)
    canonical_url = models.URLField(max_length=512, blank=True, null=True)
    title = models.CharField(max_length=200)
    excerpt = models.TextField(blank=True)
    content = models.TextField()
    reading_time_sec = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft", db_index=True)
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default="public")
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    author = models.ForeignKey(AuthorProfile, on_delete=models.CASCADE, related_name="posts")
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="posts"
    )
    series = models.ForeignKey(
        Series, on_delete=models.SET_NULL, null=True, blank=True, related_name="posts"
    )
    cover_media = models.ForeignKey(
        Media, on_delete=models.SET_NULL, null=True, blank=True, related_name="post_covers"
    )
    tags = models.ManyToManyField(Tag, through="PostTag", related_name="posts")
    seo_title = models.CharField(max_length=255, blank=True)
    seo_description = models.CharField(max_length=500, blank=True)
    og_image = models.ForeignKey(
        Media, on_delete=models.SET_NULL, null=True, blank=True, related_name="post_og_images"
    )
    views_count = models.PositiveIntegerField(default=0)
    likes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ("-published_at",)
        verbose_name = _("Post")
        verbose_name_plural = _("Posts")
        indexes = [
            models.Index(fields=["status", "published_at"]),
            models.Index(fields=["category", "published_at"]),
        ]

    def __str__(self):
        return self.title


class PostTag(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("post", "tag")


class Comment(models.Model):
    STATUS_CHOICES = (
        ("pending", _("Pending")),
        ("approved", _("Approved")),
        ("spam", _("Spam")),
        ("removed", _("Removed")),
    )

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="comments"
    )
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies"
    )
    author_name = models.CharField(max_length=100, blank=True)
    author_email = models.EmailField(blank=True)
    content = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("created_at",)
        verbose_name = _("Comment")
        verbose_name_plural = _("Comments")
        indexes = [
            models.Index(fields=["post", "status", "created_at"]),
        ]

    def __str__(self):
        return f"Comment by {self.user or self.author_name} on {self.post}"


class Reaction(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True
    )
    reaction = models.CharField(max_length=50)  # like, emoji_code, etc.
    created_at = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(null=True, blank=True)

    # Generic relation to Post or Comment
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    target = GenericForeignKey("content_type", "object_id")

    class Meta:
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]
        unique_together = ("user", "reaction", "content_type", "object_id")

    def __str__(self):
        return f'{self.reaction} by {self.user or "Anonymous"}'

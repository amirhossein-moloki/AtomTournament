import re
from django.conf import settings
from django.db import models
from django.db.models import Count
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils.text import slugify
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django_ckeditor_5.fields import CKEditor5Field
from django.utils.translation import gettext_lazy as _
from urllib.parse import urlparse, urlunparse

from common.utils.images import convert_image_to_avif


User = get_user_model()


class PostManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset()\
            .select_related('author', 'category')\
            .prefetch_related('tags')\
            .annotate(
                comments_count=Coalesce(
                    Count('comments', filter=models.Q(comments__status='approved')), 0
                )
            )

    def published(self):
        return self.get_queryset().filter(status='published')


class Media(models.Model):
    storage_key = models.CharField(max_length=255)
    url = models.URLField()
    type = models.CharField(max_length=50)  # image/video/audio/file
    mime = models.CharField(max_length=100)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    duration = models.PositiveIntegerField(null=True, blank=True)  # in seconds
    size_bytes = models.PositiveIntegerField(default=0)
    alt_text = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or self.storage_key

    def get_download_url(self):
        if self.pk:
            return reverse('download_media', kwargs={'media_id': self.pk})
        return ""


class AuthorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    display_name = models.CharField(max_length=255)
    bio = models.TextField(blank=True)
    avatar = models.ForeignKey(Media, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.display_name


class Category(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Tag(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Series(models.Model):
    ORDER_STRATEGY_CHOICES = (
        ('manual', 'Manual'),
        ('by_date', 'By Date'),
    )
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order_strategy = models.CharField(max_length=10, choices=ORDER_STRATEGY_CHOICES, default='manual')

    class Meta:
        verbose_name_plural = "Series"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('post_detail', kwargs={'slug': self.slug})


class Post(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('review', 'Review'),
        ('scheduled', 'Scheduled'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    )
    VISIBILITY_CHOICES = (
        ('public', 'Public'),
        ('private', 'Private'),
        ('unlisted', 'Unlisted'),
    )

    slug = models.SlugField(unique=True, blank=True)
    canonical_url = models.URLField(null=True, blank=True)
    title = models.CharField(max_length=255)
    excerpt = models.TextField()
    content = CKEditor5Field(config_name="default")
    reading_time_sec = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='public')
    published_at = models.DateTimeField(null=True, blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    author = models.ForeignKey(AuthorProfile, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    series = models.ForeignKey(Series, on_delete=models.SET_NULL, null=True, blank=True)
    cover_media = models.ForeignKey(Media, on_delete=models.SET_NULL, null=True, blank=True, related_name='post_covers')
    seo_title = models.CharField(max_length=255, blank=True)
    seo_description = models.TextField(blank=True)
    og_image = models.ForeignKey(Media, on_delete=models.SET_NULL, null=True, blank=True, related_name='post_og_images')
    views_count = models.PositiveIntegerField(default=0)
    likes_count = models.PositiveIntegerField(default=0)
    tags = models.ManyToManyField(Tag, through='PostTag')
    reactions = GenericRelation('Reaction', object_id_field='object_id', content_type_field='content_type')

    objects = PostManager()

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)

        original_slug = self.slug
        queryset = Post.objects.all()
        if self.pk:
            queryset = queryset.exclude(pk=self.pk)

        # Ensure slug is unique
        counter = 1
        while queryset.filter(slug=self.slug).exists():
            self.slug = f'{original_slug}-{counter}'
            counter += 1

        if self.content:
            words = re.findall(r'\w+', self.content)
            word_count = len(words)
            reading_time_minutes = word_count / 200  # Average reading speed
            self.reading_time_sec = int(reading_time_minutes * 60)
        else:
            self.reading_time_sec = 0
        super().save(*args, **kwargs)


class PostTag(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'tag')


class Revision(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    editor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    content = CKEditor5Field(config_name="default")
    title = models.CharField(max_length=255)
    excerpt = models.TextField()
    change_note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Revision for {self.post.title} at {self.created_at}"


class Comment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('spam', 'Spam'),
        ('removed', 'Removed'),
    )
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    content = CKEditor5Field(config_name="default")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    reactions = GenericRelation('Reaction', object_id_field='object_id', content_type_field='content_type')

    def __str__(self):
        return f"Comment by {self.user} on {self.post.title}"


class Reaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reaction = models.CharField(max_length=50)  # like|emoji_code
    created_at = models.DateTimeField(auto_now_add=True)

    # Generic Foreign Key setup
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        unique_together = ('user', 'content_type', 'object_id', 'reaction')

    def __str__(self):
        return f"{self.user}'s {self.reaction} on {self.content_object}"


class Page(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=255)
    content = CKEditor5Field(config_name="default")
    status = models.CharField(max_length=10, choices=Post.STATUS_CHOICES, default='draft')
    published_at = models.DateTimeField(null=True, blank=True)
    seo_title = models.CharField(max_length=255, blank=True)
    seo_description = models.TextField(blank=True)

    def __str__(self):
        return self.title


class Menu(models.Model):
    LOCATION_CHOICES = (
        ('header', 'Header'),
        ('footer', 'Footer'),
        ('sidebar', 'Sidebar'),
    )
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=10, choices=LOCATION_CHOICES, unique=True)

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    label = models.CharField(max_length=255)
    url = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    target_blank = models.BooleanField(default=False)

    def __str__(self):
        return self.label


class CustomAttachment(models.Model):
    file = models.FileField(upload_to="attachments/")
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        import os

        if self.file:
            # Check if the file is an image by extension
            filename = self.file.name
            is_image = False
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
            if any(filename.lower().endswith(ext) for ext in image_extensions):
                is_image = True

            # Avoid re-conversion loop by checking the extension
            if is_image and not self.file.name.lower().endswith('.avif'):
                # The convert_image_to_avif function returns a ContentFile
                # with the correct name (.avif extension)
                self.file = convert_image_to_avif(self.file)

        super().save(*args, **kwargs)

    def __str__(self):
        return os.path.basename(self.file.name)

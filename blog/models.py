from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Media(models.Model):
    storage_key = models.CharField(max_length=255)
    url = models.URLField()
    type = models.CharField(max_length=50)  # image/video/audio/file
    mime = models.CharField(max_length=100)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    duration = models.PositiveIntegerField(null=True, blank=True)  # in seconds
    size_bytes = models.PositiveIntegerField()
    alt_text = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or self.storage_key


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

    slug = models.SlugField(unique=True)
    canonical_url = models.URLField(null=True, blank=True)
    title = models.CharField(max_length=255)
    excerpt = models.TextField()
    content = models.TextField()  # Assuming RichText or Markdown is handled on the frontend
    reading_time_sec = models.PositiveIntegerField()
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
    comments_count = models.PositiveIntegerField(default=0)
    tags = models.ManyToManyField(Tag, through='PostTag')

    def __str__(self):
        return self.title


class PostTag(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'tag')


class Revision(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    editor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    content = models.TextField()
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
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    author_name = models.CharField(max_length=255)
    author_email = models.EmailField()
    content = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Comment by {self.author_name} on {self.post.title}"


class Reaction(models.Model):
    TARGET_TYPE_CHOICES = (
        ('post', 'Post'),
        ('comment', 'Comment'),
    )
    target_type = models.CharField(max_length=10, choices=TARGET_TYPE_CHOICES)
    target_id = models.PositiveIntegerField()
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    reaction = models.CharField(max_length=50)  # like|emoji_code
    created_at = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(null=True, blank=True)

    def __str__(self):
        return f"{self.reaction} on {self.target_type} {self.target_id}"


class Page(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=255)
    content = models.TextField()
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

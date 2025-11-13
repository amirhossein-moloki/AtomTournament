from django.contrib import admin
from django.utils.safestring import mark_safe
from django_summernote.admin import SummernoteModelAdmin
from .forms import AuthorProfileForm
from .models import (
    AuthorProfile, Category, Tag, Post, PostTag, Series, Media, Revision,
    Comment, Reaction, Page, Menu, MenuItem
)


@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ('title', 'type', 'mime', 'size_bytes', 'created_at', 'image_preview')
    list_filter = ('type', 'mime')
    search_fields = ('title', 'alt_text')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.type == 'image' and obj.url:
            return mark_safe(f'<img src="{obj.url}" style="max-height: 100px; max-width: 100px;" />')
        return "No Preview"
    image_preview.short_description = 'Preview'


@admin.register(AuthorProfile)
class AuthorProfileAdmin(admin.ModelAdmin):
    form = AuthorProfileForm
    list_display = ('display_name', 'user')
    search_fields = ('display_name', 'user__username')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent', 'order')
    list_filter = ('parent',)
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Series)
class SeriesAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'order_strategy')
    search_fields = ('title',)
    prepopulated_fields = {'slug': ('title',)}


class PostTagInline(admin.TabularInline):
    model = PostTag
    extra = 1


@admin.register(Post)
class PostAdmin(SummernoteModelAdmin):
    summernote_fields = ('content',)
    list_display = ('title', 'slug', 'author', 'category', 'status', 'visibility', 'published_at', 'views_count', 'likes_count')
    list_filter = ('status', 'visibility', 'category', 'author')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [PostTagInline]
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'author', 'content', 'excerpt')
        }),
        ('Metadata', {
            'fields': ('status', 'visibility', 'published_at', 'scheduled_at')
        }),
        ('Categorization', {
            'fields': ('category', 'series')
        }),
        ('Media', {
            'fields': ('cover_media', 'og_image')
        }),
        ('SEO', {
            'classes': ('collapse',),
            'fields': ('seo_title', 'seo_description', 'canonical_url')
        }),
        ('Counters', {
            'classes': ('collapse',),
            'fields': ('views_count', 'likes_count', 'comments_count', 'reading_time_sec')
        }),
    )
    readonly_fields = ('views_count', 'likes_count', 'comments_count')


@admin.register(Revision)
class RevisionAdmin(admin.ModelAdmin):
    list_display = ('post', 'editor', 'created_at')
    list_filter = ('editor',)
    search_fields = ('post__title',)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author_name', 'post', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('author_name', 'author_email', 'content')


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ('target_type', 'target_id', 'reaction', 'user', 'created_at')
    list_filter = ('target_type', 'reaction')


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'status', 'published_at')
    list_filter = ('status',)
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}


class MenuItemInline(admin.TabularInline):
    model = MenuItem
    extra = 1


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ('name', 'location')
    list_filter = ('location',)
    inlines = [MenuItemInline]

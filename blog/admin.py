from django.contrib import admin
from .models import (
    AuthorProfile, Category, Tag, Post, PostTag, Series, Media, Revision,
    Comment, Reaction, Page, Menu, MenuItem
)


@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ('title', 'type', 'mime', 'size_bytes', 'created_at')
    list_filter = ('type', 'mime')
    search_fields = ('title', 'alt_text')


@admin.register(AuthorProfile)
class AuthorProfileAdmin(admin.ModelAdmin):
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
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'author', 'category', 'status', 'published_at')
    list_filter = ('status', 'visibility', 'category', 'author')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [PostTagInline]


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

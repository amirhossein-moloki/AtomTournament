from django.contrib import admin, messages
from django.db import transaction
from jalali_date.admin import ModelAdminJalaliMixin
from .models import (
    AuthorProfile, Category, Tag, Post, PostTag, Series, Media, Revision,
    Comment, Reaction, Page, Menu, MenuItem, PostMedia
)


from django.core.files.storage import default_storage
from common.utils.files import get_sanitized_filename
from .forms import MediaAdminForm, PageAdminForm, PostAdminForm

@admin.register(Media)
class MediaAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    form = MediaAdminForm
    list_display = ('title', 'type', 'mime', 'size_bytes', 'created_at', 'get_download_url')
    list_filter = ('type', 'mime')
    search_fields = ('title', 'alt_text')
    readonly_fields = ('storage_key', 'url', 'type', 'mime', 'size_bytes', 'uploaded_by', 'created_at', 'get_download_url')

    def save_model(self, request, obj, form, change):
        uploaded_file = form.cleaned_data.get('file')
        if uploaded_file:
            sanitized_name = get_sanitized_filename(uploaded_file.name)
            storage_key = default_storage.save(sanitized_name, uploaded_file)
            file_url = default_storage.url(storage_key)

            obj.storage_key = storage_key
            obj.url = file_url
            obj.mime = uploaded_file.content_type
            obj.size_bytes = uploaded_file.size
            obj.title = sanitized_name
            if 'image' in obj.mime:
                obj.type = 'image'
            elif 'video' in obj.mime:
                obj.type = 'video'
            else:
                obj.type = 'file'

        if not obj.pk:  # If creating a new object
            obj.uploaded_by = request.user

        super().save_model(request, obj, form, change)


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


class PostMediaInline(admin.TabularInline):
    model = PostMedia
    readonly_fields = ('media', 'attachment_type')
    extra = 0
    verbose_name = 'Attachment'
    verbose_name_plural = 'Attachments'

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Post)
class PostAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    form = PostAdminForm
    list_display = ('title', 'slug', 'author', 'category', 'status', 'published_at')
    list_filter = ('status', 'visibility', 'category', 'author')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    autocomplete_fields = ('cover_media', 'og_image')
    inlines = [PostTagInline, PostMediaInline]
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'author', 'content', 'excerpt')
        }),
        ('Metadata', {
            'fields': ('category', 'series')
        }),
        ('Media', {
            'fields': ('cover_media', 'og_image')
        }),
        ('Status & Visibility', {
            'fields': ('status', 'visibility', 'published_at', 'scheduled_at')
        }),
        ('SEO', {
            'classes': ('collapse',),
            'fields': ('seo_title', 'seo_description', 'canonical_url')
        }),
    )

    def save_model(self, request, obj, form, change):
        try:
            super().save_model(request, obj, form, change)
        except Exception as e:
            messages.set_level(request, messages.ERROR)
            self.message_user(
                request,
                f"خطایی در هنگام ذخیره پست رخ داد: {e}",
                level=messages.ERROR
            )


@admin.register(Revision)
class RevisionAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    list_display = ('post', 'editor', 'created_at')
    list_filter = ('editor',)
    search_fields = ('post__title',)


@admin.register(Comment)
class CommentAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    list_display = ('user', 'post', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__username', 'content')


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'reaction', 'content_object', 'created_at')
    list_filter = ('reaction',)


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    form = PageAdminForm
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

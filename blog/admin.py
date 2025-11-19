from django.contrib import admin, messages
from django_summernote.admin import SummernoteModelAdmin
from django_summernote.models import Attachment
from .models import (
    AuthorProfile, Category, Tag, Post, PostTag, Series, Media, Revision,
    Comment, Reaction, Page, Menu, MenuItem
)
from .attachments import CustomAttachment


from django.core.files.storage import default_storage
from .forms import MediaAdminForm

@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    form = MediaAdminForm
    list_display = ('title', 'type', 'mime', 'size_bytes', 'created_at')
    list_filter = ('type', 'mime')
    search_fields = ('title', 'alt_text')
    readonly_fields = ('storage_key', 'url', 'type', 'mime', 'size_bytes', 'uploaded_by', 'created_at')

    def save_model(self, request, obj, form, change):
        uploaded_file = form.cleaned_data.get('file')
        if uploaded_file:
            storage_key = default_storage.save(uploaded_file.name, uploaded_file)
            file_url = default_storage.url(storage_key)

            obj.storage_key = storage_key
            obj.url = file_url
            obj.mime = uploaded_file.content_type
            obj.size_bytes = uploaded_file.size
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


@admin.register(Post)
class PostAdmin(SummernoteModelAdmin):
    summernote_fields = ('content',)
    list_display = ('title', 'slug', 'author', 'category', 'status', 'published_at')
    list_filter = ('status', 'visibility', 'category', 'author')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [PostTagInline]
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
class RevisionAdmin(admin.ModelAdmin):
    list_display = ('post', 'editor', 'created_at')
    list_filter = ('editor',)
    search_fields = ('post__title',)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__username', 'content')


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'reaction', 'content_object', 'created_at')
    list_filter = ('reaction',)


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


class CustomAttachmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'file', 'uploaded']
    search_fields = ['name']
    list_filter = ['uploaded']
    actions = ['delete_selected']

    def save_model(self, request, obj, form, change):
        obj.save(request=request)


# Unregister the default Attachment admin if it's registered
try:
    admin.site.unregister(Attachment)
except admin.sites.NotRegistered:
    pass

# Unregister the CustomAttachment model if it's already registered
try:
    admin.site.unregister(CustomAttachment)
except admin.sites.NotRegistered:
    pass

# Register the CustomAttachment model with the custom admin
admin.site.register(CustomAttachment, CustomAttachmentAdmin)

from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from simple_history.admin import SimpleHistoryAdmin
from .models import (
    Post,
    Category,
    Tag,
    Comment,
    AuthorProfile,
    Media,
    Series,
    Reaction,
    Page,
    Revision,
    Menu,
    MenuItem,
    Role,
    Permission,
    PostTag,
)


class PostTagInline(TabularInline):
    model = PostTag
    extra = 1
    autocomplete_fields = ["tag"]


@admin.register(Post)
class PostAdmin(SimpleHistoryAdmin, ModelAdmin):
    list_display = (
        "title",
        "slug",
        "author",
        "category",
        "status",
        "visibility",
        "published_at",
    )
    list_filter = ("status", "visibility", "category", "author")
    search_fields = ("title", "content", "excerpt")
    autocomplete_fields = ("author", "category", "series", "cover_media", "og_image")
    inlines = [PostTagInline]

    fieldsets = (
        (
            "Main Content",
            {
                "fields": ("title", "slug", "content", "excerpt"),
                "classes": ("tab",),
            },
        ),
        (
            "Metadata & Publishing",
            {
                "fields": (
                    "author",
                    "category",
                    "series",
                    "status",
                    "visibility",
                    "published_at",
                    "scheduled_at",
                    "cover_media",
                ),
                "classes": ("tab",),
            },
        ),
        (
            "SEO",
            {
                "fields": ("seo_title", "seo_description", "og_image", "canonical_url"),
                "classes": ("tab",),
            },
        ),
    )


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ("name", "slug", "parent", "order")
    list_filter = ("parent",)
    search_fields = ("name", "description")
    autocomplete_fields = ["parent"]


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)


@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    list_display = ("post", "user", "author_name", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("content", "author_name", "user__username")
    autocomplete_fields = ["post", "user", "parent"]


@admin.register(AuthorProfile)
class AuthorProfileAdmin(ModelAdmin):
    list_display = ("display_name", "user")
    search_fields = ("display_name", "user__username")
    autocomplete_fields = ["user", "avatar"]


@admin.register(Media)
class MediaAdmin(ModelAdmin):
    list_display = ("title", "type", "uploaded_by", "created_at")
    list_filter = ("type",)
    search_fields = ("title", "storage_key")
    autocomplete_fields = ["uploaded_by"]


@admin.register(Series)
class SeriesAdmin(ModelAdmin):
    list_display = ("title", "slug", "order_strategy")
    search_fields = ("title", "description")


@admin.register(Reaction)
class ReactionAdmin(ModelAdmin):
    list_display = ("target", "reaction", "user", "created_at")
    list_filter = ("reaction", "content_type")
    autocomplete_fields = ["user"]


@admin.register(Page)
class PageAdmin(ModelAdmin):
    list_display = ("title", "slug", "status", "published_at")
    list_filter = ("status",)
    search_fields = ("title", "content")


@admin.register(Revision)
class RevisionAdmin(ModelAdmin):
    list_display = ("post", "editor", "created_at")
    list_filter = ("editor",)
    autocomplete_fields = ["post", "editor"]


class MenuItemInline(TabularInline):
    model = MenuItem
    extra = 1


@admin.register(Menu)
class MenuAdmin(ModelAdmin):
    list_display = ("name", "location")
    inlines = [MenuItemInline]


@admin.register(Role)
class RoleAdmin(ModelAdmin):
    list_display = ("name",)
    filter_horizontal = ("permissions",)


@admin.register(Permission)
class PermissionAdmin(ModelAdmin):
    list_display = ("code", "description")
    search_fields = ("code", "description")

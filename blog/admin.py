from django.contrib import admin
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


class PostTagInline(admin.TabularInline):
    model = PostTag
    extra = 1


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
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
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "published_at"
    ordering = ("-published_at",)
    inlines = [PostTagInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent", "order")
    list_filter = ("parent",)
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("post", "user", "author_name", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("content", "author_name", "user__username")


@admin.register(AuthorProfile)
class AuthorProfileAdmin(admin.ModelAdmin):
    list_display = ("display_name", "user")
    search_fields = ("display_name", "user__username")


@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ("title", "type", "uploaded_by", "created_at")
    list_filter = ("type",)
    search_fields = ("title", "storage_key")


@admin.register(Series)
class SeriesAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "order_strategy")
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ("target", "reaction", "user", "created_at")
    list_filter = ("reaction", "content_type")


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "status", "published_at")
    list_filter = ("status",)
    search_fields = ("title", "content")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Revision)
class RevisionAdmin(admin.ModelAdmin):
    list_display = ("post", "editor", "created_at")
    list_filter = ("editor",)


class MenuItemInline(admin.TabularInline):
    model = MenuItem
    extra = 1


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ("name", "location")
    inlines = [MenuItemInline]


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name",)
    filter_horizontal = ("permissions",)


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("code", "description")
    search_fields = ("code", "description")

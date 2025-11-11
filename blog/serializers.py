from rest_framework import serializers
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
)
from users.models import User


class MediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Media
        fields = "__all__"


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug", "description"]


class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "parent", "description", "order", "children"]

    def get_children(self, obj):
        if obj.children.exists():
            return CategorySerializer(obj.children.all(), many=True).data
        return None


class AuthorProfileSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source="user.username")
    avatar = MediaSerializer(read_only=True)

    class Meta:
        model = AuthorProfile
        fields = ["id", "user", "display_name", "bio", "avatar", "social_links"]


class SeriesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Series
        fields = "__all__"


class PostSerializer(serializers.ModelSerializer):
    author = AuthorProfileSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    cover_media = MediaSerializer(read_only=True)
    og_image = MediaSerializer(read_only=True)

    class Meta:
        model = Post
        fields = [
            "id",
            "slug",
            "title",
            "excerpt",
            "content",
            "status",
            "visibility",
            "published_at",
            "author",
            "category",
            "tags",
            "series",
            "cover_media",
            "seo_title",
            "seo_description",
            "og_image",
            "views_count",
            "likes_count",
            "comments_count",
        ]


class CommentSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source="user.username")
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            "id",
            "post",
            "author",
            "author_name",
            "content",
            "created_at",
            "parent",
            "replies",
            "status",
        ]
        read_only_fields = ["status"]

    def get_replies(self, obj):
        if obj.replies.exists():
            return CommentSerializer(obj.replies.all(), many=True).data
        return None


class ReactionSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source="user.username")

    class Meta:
        model = Reaction
        fields = "__all__"


class PageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = "__all__"


class RevisionSerializer(serializers.ModelSerializer):
    editor = serializers.ReadOnlyField(source="editor.username")

    class Meta:
        model = Revision
        fields = "__all__"


class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = "__all__"


class MenuSerializer(serializers.ModelSerializer):
    items = MenuItemSerializer(many=True, read_only=True)

    class Meta:
        model = Menu
        fields = ["id", "name", "location", "items"]


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = "__all__"


class RoleSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)

    class Meta:
        model = Role
        fields = ["id", "name", "description", "permissions"]

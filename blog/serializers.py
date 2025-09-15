from rest_framework import serializers
from .models import Post, Tag, Category, Comment
from users.serializers import UserSerializer


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name", "slug")


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug")


class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ("id", "post", "author", "content", "created_at")
        read_only_fields = ("post", "author")


class PostListSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = Post
        fields = (
            "id",
            "title",
            "slug",
            "author",
            "content",
            "featured_image",
            "status",
            "created_at",
            "updated_at",
            "category",
            "tags",
        )


class PostDetailSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), required=False)
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True, required=False)
    related_posts = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            "id",
            "title",
            "author",
            "content",
            "featured_image",
            "status",
            "created_at",
            "updated_at",
            "category",
            "tags",
            "comments",
            "related_posts",
        )
        read_only_fields = ("author", "created_at", "updated_at", "comments")

    def get_related_posts(self, obj):
        from .models import Post
        from django.db.models import Count

        post_tags_ids = obj.tags.values_list("id", flat=True)
        similar_posts = (
            Post.objects.filter(status="published", tags__in=post_tags_ids)
            .exclude(id=obj.id)
            .annotate(same_tags=Count("tags"))
            .order_by("-same_tags", "-created_at")[:4]
        )
        return PostListSerializer(similar_posts, many=True).data

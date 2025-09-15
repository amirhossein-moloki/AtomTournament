from rest_framework import serializers
from .models import Post, Tag, Category, Comment, CommentReaction, CommentReport
from users.serializers import UserSerializer


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name", "slug")


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug")


from django.db.models import Count


class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    reactions = serializers.SerializerMethodField()
    user_reaction = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = (
            "id",
            "post",
            "author",
            "content",
            "created_at",
            "parent",
            "replies",
            "reactions",
            "user_reaction",
        )
        read_only_fields = ("post", "author", "replies", "reactions", "user_reaction")

    def get_replies(self, obj):
        # Only serialize top-level replies to avoid excessive nesting
        if obj.replies.exists():
            # Pass context to the nested serializer
            return CommentSerializer(obj.replies.filter(parent=obj), many=True, context=self.context).data
        return []

    def get_reactions(self, obj):
        #  Returns a dictionary of reaction counts, e.g., {"like": 10, "love": 5}
        return (
            CommentReaction.objects.filter(comment=obj)
            .values("reaction_type")
            .annotate(count=Count("reaction_type"))
            .order_by("-count")
        )

    def get_user_reaction(self, obj):
        # Returns the reaction type the current user has given, or None
        user = self.context["request"].user
        if user.is_authenticated:
            try:
                reaction = CommentReaction.objects.get(comment=obj, user=user)
                return reaction.reaction_type
            except CommentReaction.DoesNotExist:
                return None
        return None


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
    comments = serializers.SerializerMethodField()
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

    def get_comments(self, obj):
        top_level_comments = obj.comments.filter(parent__isnull=True)
        return CommentSerializer(top_level_comments, many=True, context=self.context).data

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


class CommentReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommentReport
        fields = ["id", "reason", "comment", "reporter", "status", "created_at"]
        read_only_fields = ["comment", "reporter", "status", "created_at"]

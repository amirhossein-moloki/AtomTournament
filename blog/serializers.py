from rest_framework import serializers
from .models import (
    AuthorProfile, Category, Tag, Post, PostTag, Series, Media, Revision,
    Comment, Reaction, Page, Menu, MenuItem
)


class MediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Media
        fields = '__all__'


class AuthorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthorProfile
        fields = ('user', 'display_name', 'bio', 'avatar')


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'


class SeriesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Series
        fields = '__all__'


class PostTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostTag
        fields = '__all__'


class AuthorForPostSerializer(serializers.ModelSerializer):
    """Abbreviated Author serializer for nested display inside Post."""
    class Meta:
        model = AuthorProfile
        fields = ('display_name', 'avatar')


class CommentForPostSerializer(serializers.ModelSerializer):
    """Abbreviated Comment serializer for nested display."""
    user = serializers.StringRelatedField() # Display user's string representation

    class Meta:
        model = Comment
        fields = ('id', 'user', 'author_name', 'content', 'created_at', 'parent')


class PostListSerializer(serializers.ModelSerializer):
    """Serializer for listing posts - less detail."""
    author = AuthorForPostSerializer(read_only=True)
    category = serializers.StringRelatedField()
    cover_media = MediaSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = Post
        fields = (
            'id', 'slug', 'title', 'excerpt', 'reading_time_sec', 'status',
            'visibility', 'published_at', 'author', 'category', 'cover_media',
            'views_count', 'likes_count', 'comments_count', 'tags'
        )


class PostDetailSerializer(serializers.ModelSerializer):
    """Serializer for a single post - full detail."""
    author = AuthorForPostSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    series = SeriesSerializer(read_only=True)
    cover_media = MediaSerializer(read_only=True)
    og_image = MediaSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    comments = CommentForPostSerializer(many=True, read_only=True) # Assuming a related_name='comments' on Post model for Comments
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.all(), source='tags', write_only=True,
        help_text="List of Tag IDs to associate with the post."
    )

    class Meta:
        model = Post
        fields = '__all__'
        read_only_fields = ('author', 'views_count', 'likes_count', 'comments_count')


# Let's keep the original PostSerializer for creation/update, or adapt the DetailSerializer.
# For simplicity, we can use the detail serializer for write operations and just control read_only fields.
PostSerializer = PostDetailSerializer


class RevisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Revision
        fields = '__all__'


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = '__all__'


class ReactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reaction
        fields = '__all__'


class PageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = '__all__'


class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = '__all__'


class MenuSerializer(serializers.ModelSerializer):
    items = MenuItemSerializer(many=True, read_only=True)

    class Meta:
        model = Menu
        fields = '__all__'

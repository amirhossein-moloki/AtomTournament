from rest_framework import serializers
from .models import (
    AuthorProfile, Category, Tag, Post, Series, Media,
    Comment, Reaction, Page, Menu, MenuItem, Revision
)


class MediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Media
        fields = '__all__'


class AuthorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthorProfile
        fields = ('user', 'display_name', 'bio', 'avatar')


class AuthorForPostSerializer(serializers.ModelSerializer):
    avatar = MediaSerializer(read_only=True)

    class Meta:
        model = AuthorProfile
        fields = ('display_name', 'avatar')


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('slug', 'name', 'parent')


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('slug', 'name')


class SeriesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Series
        fields = '__all__'


class CommentForPostSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = Comment
        fields = ('id', 'user', 'content', 'created_at', 'parent')


class PostListSerializer(serializers.ModelSerializer):
    author = AuthorForPostSerializer(read_only=True)
    category = serializers.StringRelatedField()
    cover_media = MediaSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    likes_count = serializers.SerializerMethodField()
    comments_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Post
        fields = (
            'slug', 'title', 'excerpt', 'reading_time_sec', 'status',
            'published_at', 'author', 'category', 'cover_media',
            'views_count', 'likes_count', 'comments_count', 'tags'
        )

    def get_likes_count(self, obj):
        return obj.reactions.filter(reaction='like').count()


class PostDetailSerializer(PostListSerializer):
    series = SeriesSerializer(read_only=True)
    og_image = MediaSerializer(read_only=True)
    comments = CommentForPostSerializer(many=True, read_only=True)
    content = serializers.CharField()

    class Meta(PostListSerializer.Meta):
        fields = PostListSerializer.Meta.fields + (
            'content', 'canonical_url', 'series', 'seo_title',
            'seo_description', 'og_image', 'comments'
        )


class PostCreateUpdateSerializer(serializers.ModelSerializer):
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.all(), source='tags', required=False
    )
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', required=False
    )

    class Meta:
        model = Post
        fields = (
            'title', 'excerpt', 'content', 'status', 'visibility',
            'published_at', 'scheduled_at', 'category_id', 'series',
            'cover_media', 'seo_title', 'seo_description', 'og_image',
            'tag_ids', 'slug', 'canonical_url', 'likes_count', 'views_count',
            'reading_time_sec'
        )
        read_only_fields = (
            'likes_count', 'views_count', 'reading_time_sec'
        )
        extra_kwargs = {
            'slug': {'required': False}
        }


class RevisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Revision
        fields = '__all__'


class CommentSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Comment
        fields = ('id', 'post', 'user', 'parent', 'content', 'created_at', 'status')


from django.contrib.contenttypes.models import ContentType

class ReactionSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Reaction
        fields = ('id', 'user', 'reaction', 'content_type', 'object_id', 'created_at')

    def validate(self, attrs):
        content_type = attrs['content_type']
        object_id = attrs['object_id']
        ModelClass = content_type.model_class()

        if not ModelClass.objects.filter(pk=object_id).exists():
            raise serializers.ValidationError("The target object does not exist.")

        return attrs


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

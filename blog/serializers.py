from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from markdownify import markdownify as html_to_markdown

from common.utils.files import get_sanitized_filename
from .models import (
    AuthorProfile, Category, Tag, Post, Series, Media,
    Comment, Reaction, Page, Menu, MenuItem, Revision, PostMedia
)
from .mixins import DynamicFieldsMixin


User = get_user_model()


class ContentNormalizationMixin:
    content_field_name = "content"

    def _normalize_content(self, value: str) -> str:
        normalized = html_to_markdown(
            value,
            strip=["script", "style"],
            preserve_br=True,
            heading_style="ATX",
            escape_asterisks=False,
            escape_underscores=False,
            escape_md=False,
        )
        return normalized.replace("\xa0", " ").strip()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        content_value = data.get(self.content_field_name)
        if isinstance(content_value, str) and content_value.strip():
            data[self.content_field_name] = self._normalize_content(content_value)
        return data

class MediaDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Media
        fields = (
            'id', 'storage_key', 'url', 'type', 'mime',
            'width', 'height', 'duration', 'size_bytes',
            'alt_text', 'title', 'uploaded_by', 'created_at'
        )

class MediaCreateSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)

    class Meta:
        model = Media
        fields = ('file', 'alt_text', 'title')

    def create(self, validated_data):
        uploaded_file = validated_data.pop('file')

        # Sanitize the filename before saving
        sanitized_name = get_sanitized_filename(uploaded_file.name)
        storage_key = default_storage.save(sanitized_name, uploaded_file)
        file_url = default_storage.url(storage_key)

        # If title is not provided, use the sanitized name
        if not validated_data.get('title'):
            validated_data['title'] = sanitized_name

        # Populate model fields
        validated_data['storage_key'] = storage_key
        validated_data['url'] = file_url
        validated_data['mime'] = uploaded_file.content_type
        validated_data['size_bytes'] = uploaded_file.size

        # Determine the 'type' based on the mime type
        if 'image' in validated_data['mime']:
            validated_data['type'] = 'image'
        elif 'video' in validated_data['mime']:
            validated_data['type'] = 'video'
        else:
            validated_data['type'] = 'file'

        # The 'uploaded_by' field is passed from the view
        media = Media.objects.create(**validated_data)
        return media


class AuthorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthorProfile
        fields = ('user', 'display_name', 'bio', 'avatar')


class AuthorForPostSerializer(serializers.ModelSerializer):
    avatar = MediaDetailSerializer(read_only=True)

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


class PostListSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    author = AuthorForPostSerializer(read_only=True)
    category = serializers.StringRelatedField()
    cover_media = MediaDetailSerializer(read_only=True)
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


class PostDetailSerializer(ContentNormalizationMixin, PostListSerializer):
    series = SeriesSerializer(read_only=True)
    og_image = MediaDetailSerializer(read_only=True)
    comments = CommentForPostSerializer(many=True, read_only=True)
    content = serializers.CharField()

    media_attachments = serializers.SerializerMethodField()

    class Meta(PostListSerializer.Meta):
        fields = PostListSerializer.Meta.fields + (
            'content', 'canonical_url', 'series', 'seo_title',
            'seo_description', 'og_image', 'comments', 'media_attachments'
        )

    def get_media_attachments(self, obj):
        return PostMediaSerializer(obj.media_attachments.all(), many=True).data


class PostMediaSerializer(serializers.ModelSerializer):
    media = MediaDetailSerializer(read_only=True)

    class Meta:
        model = PostMedia
        fields = ('media', 'attachment_type')


class PostCreateUpdateSerializer(ContentNormalizationMixin, serializers.ModelSerializer):
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.all(), source='tags', required=False, write_only=True
    )
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', required=False, write_only=True
    )
    cover_media_id = serializers.PrimaryKeyRelatedField(
        queryset=Media.objects.all(), source='cover_media', required=False, allow_null=True, write_only=True
    )
    og_image_id = serializers.PrimaryKeyRelatedField(
        queryset=Media.objects.all(), source='og_image', required=False, allow_null=True, write_only=True
    )

    cover_media = MediaDetailSerializer(read_only=True)
    og_image = MediaDetailSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Post
        fields = (
            'title', 'excerpt', 'content', 'status', 'visibility',
            'published_at', 'scheduled_at', 'category', 'series',
            'cover_media', 'seo_title', 'seo_description', 'og_image',
            'tags', 'slug', 'canonical_url', 'likes_count', 'views_count',
            'reading_time_sec', 'tag_ids', 'category_id', 'cover_media_id', 'og_image_id'
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

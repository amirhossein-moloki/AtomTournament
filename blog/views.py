from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    Post, AuthorProfile, Category, Tag, Series, Media, Revision,
    Comment, Reaction, Page, Menu, MenuItem
)
from .serializers import (
    PostListSerializer, PostDetailSerializer, PostCreateUpdateSerializer,
    AuthorProfileSerializer, CategorySerializer, TagSerializer, SeriesSerializer,
    MediaDetailSerializer, MediaCreateSerializer, RevisionSerializer, CommentSerializer, ReactionSerializer,
    PageSerializer, MenuSerializer, MenuItemSerializer
)
from .filters import PostFilter
from .pagination import CustomPageNumberPagination
from .permissions import IsOwnerOrReadOnly, IsAdminUserOrReadOnly, IsAuthorOrAdminOrReadOnly
from users.permissions import IsOwnerOrAdmin
from .tasks import notify_author_on_new_comment
from .exceptions import custom_exception_handler
import uuid
import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from .mixins import DynamicSerializerViewMixin
from rest_framework.views import APIView

class BaseBlogAPIView(APIView):
    def handle_exception(self, exc):
        """
        Handle any exception that occurs, by delegating to the custom exception handler.
        """
        return custom_exception_handler(exc, self.get_exception_handler_context())


class PostViewSet(DynamicSerializerViewMixin, viewsets.ModelViewSet):
    queryset = Post.objects.all()
    permission_classes = [IsAuthorOrAdminOrReadOnly]
    pagination_class = CustomPageNumberPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = PostFilter
    search_fields = ['title', 'content', 'excerpt']
    ordering_fields = ['published_at', 'views_count', 'id']
    ordering = ['-published_at', '-id']
    lookup_field = 'slug'

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return PostCreateUpdateSerializer
        elif self.action == 'retrieve':
            return PostDetailSerializer
        return PostListSerializer

    def get_queryset(self):
        if self.action == 'list':
            queryset = Post.objects.all()
            fields_query = self.request.query_params.get('fields')
            fields = {f.strip() for f in fields_query.split(',')} if fields_query else set()

            selects = set()
            prefetches = set()

            # Define a default set of fields for optimization if none are provided.
            if not fields:
                fields = {'slug', 'title', 'excerpt', 'author', 'category', 'cover_media', 'tags', 'likes_count', 'comments_count'}

            if 'author' in fields:
                selects.add('author__avatar')
            if 'category' in fields:
                selects.add('category')
            if 'cover_media' in fields:
                selects.add('cover_media')
            if 'tags' in fields:
                prefetches.add('tags')
            if 'likes_count' in fields:
                prefetches.add('reactions')

            if selects:
                queryset = queryset.select_related(*selects)
            if prefetches:
                queryset = queryset.prefetch_related(*prefetches)

            queryset = queryset.annotate(comments_count=Count('comments'))

            user = self.request.user
            if user.is_authenticated and user.is_staff:
                return queryset
            if user.is_authenticated:
                return queryset.filter(
                    Q(status='published', published_at__lte=timezone.now()) |
                    Q(author__user=user, status__in=['draft', 'review'])
                ).distinct()
            return queryset.filter(status='published', published_at__lte=timezone.now())
        else:
            queryset = Post.objects.all()
            fields_query = self.request.query_params.get('fields')
            fields = {f.strip() for f in fields_query.split(',')} if fields_query else {'all'}

            selects = set()
            prefetches = set()
            all_fields = 'all' in fields

            if all_fields or 'author' in fields:
                selects.add('author__avatar')
            if all_fields or 'category' in fields:
                selects.add('category')
            if all_fields or 'cover_media' in fields:
                selects.add('cover_media')
            if all_fields or 'series' in fields:
                selects.add('series')
            if all_fields or 'og_image' in fields:
                selects.add('og_image')
            if all_fields or 'tags' in fields:
                prefetches.add('tags')
            if all_fields or 'likes_count' in fields:
                prefetches.add('reactions')
            if all_fields or 'comments' in fields:
                prefetches.add('comments__user')
            if all_fields or 'media_attachments' in fields:
                prefetches.add('media_attachments__media')

            if selects:
                queryset = queryset.select_related(*selects)
            if prefetches:
                queryset = queryset.prefetch_related(*prefetches)
            return queryset

    def perform_create(self, serializer):
        author_profile, _ = AuthorProfile.objects.get_or_create(
            user=self.request.user,
            defaults={'display_name': self.request.user.username}
        )
        serializer.save(author=author_profile)

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.views_count += 1
        obj.save(update_fields=['views_count'])
        serializer = self.get_serializer(obj)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def similar(self, request, slug=None):
        try:
            current_post = self.get_object()
        except Post.DoesNotExist:
            raise NotFound('پست مورد نظر برای یافتن پست‌های مشابه پیدا نشد.')

        if not current_post.category:
            return Response([])

        similar_posts = Post.objects.filter(
            status='published',
            category=current_post.category
        ).exclude(pk=current_post.pk).order_by('-published_at', '-id')[:5]

        serializer = PostListSerializer(similar_posts, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='same-category')
    def same_category(self, request, slug=None):
        current_post = self.get_object()
        paginator = self.pagination_class()

        if not current_post.category:
            return paginator.get_paginated_response([])

        category_posts = Post.objects.filter(
            status='published',
            category=current_post.category,
            published_at__lte=timezone.now()
        ).exclude(pk=current_post.pk).order_by('-published_at', '-id')

        paginated_posts = paginator.paginate_queryset(category_posts, request, view=self)
        serializer = PostListSerializer(paginated_posts, many=True, context=self.get_serializer_context())
        return paginator.get_paginated_response(serializer.data)

    @action(detail=False, methods=['get'], url_path='slug/(?P<slug>[^/.]+)')
    def by_slug(self, request, slug=None):
        try:
            post = self.get_queryset().get(slug=slug)
        except Post.DoesNotExist:
            raise NotFound('پستی با این اسلاگ یافت نشد.')

        serializer = PostDetailSerializer(post, context=self.get_serializer_context())
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsOwnerOrReadOnly])
    def lock(self, request, slug=None):
        post = self.get_object()
        lock_expiry_minutes = getattr(settings, 'POST_LOCK_EXPIRY_MINUTES', 15)

        if post.locked_by and post.locked_by != request.user:
            # Check if lock is expired
            if post.locked_at and timezone.now() - post.locked_at > timezone.timedelta(minutes=lock_expiry_minutes):
                pass  # Allow taking over an expired lock
            else:
                return Response(
                    {'detail': f'این پست توسط کاربر دیگری قفل شده است: {post.locked_by.username}'},
                    status=status.HTTP_409_CONFLICT
                )
        post.locked_by = request.user
        post.locked_at = timezone.now()
        post.save(update_fields=['locked_by', 'locked_at'])
        return Response({'detail': 'پست با موفقیت قفل شد.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsOwnerOrReadOnly])
    def unlock(self, request, slug=None):
        post = self.get_object()
        if post.locked_by != request.user and not request.user.is_staff:
            return Response(
                {'detail': 'شما اجازه آزاد کردن قفل این پست را ندارید.'},
                status=status.HTTP_403_FORBIDDEN
            )
        post.locked_by = None
        post.locked_at = None
        post.save(update_fields=['locked_by', 'locked_at'])
        return Response({'detail': 'قفل پست با موفقیت آزاد شد.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['put'], url_path='status', permission_classes=[IsAuthenticated, IsOwnerOrReadOnly])
    def set_status(self, request, slug=None):
        post = self.get_object()
        new_status = request.data.get('status')
        if not new_status or new_status not in [choice[0] for choice in Post.STATUS_CHOICES]:
            return Response({'detail': 'وضعیت نامعتبر است.'}, status=status.HTTP_400_BAD_REQUEST)

        post.status = new_status
        if new_status == 'published' and not post.published_at:
            post.published_at = timezone.now()
        elif new_status == 'scheduled':
            scheduled_at = request.data.get('scheduled_at')
            if not scheduled_at:
                return Response({'detail': 'برای زمان‌بندی، تاریخ انتشار الزامی است.'}, status=status.HTTP_400_BAD_REQUEST)
            post.scheduled_at = scheduled_at

        post.save()
        serializer = self.get_serializer(post)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='revisions', permission_classes=[IsAuthenticated, IsOwnerOrReadOnly])
    def revisions(self, request, slug=None):
        post = self.get_object()
        revisions = Revision.objects.filter(post=post).order_by('-created_at')
        serializer = RevisionSerializer(revisions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='revisions/(?P<rev_id>[^/.]+)/rollback', permission_classes=[IsAuthenticated, IsOwnerOrReadOnly])
    def rollback(self, request, slug=None, rev_id=None):
        post = self.get_object()
        revision = get_object_or_404(Revision, post=post, pk=rev_id)

        # Create a new revision to log the rollback action
        Revision.objects.create(
            post=post,
            editor=request.user,
            title=post.title,
            excerpt=post.excerpt,
            content=post.content,
            change_note=f'بازگردانی به نسخه {revision.created_at.strftime("%Y-%m-%d %H:%M")}'
        )

        post.title = revision.title
        post.excerpt = revision.excerpt
        post.content = revision.content
        post.save()

        serializer = self.get_serializer(post)
        return Response(serializer.data)


@api_view(['GET'])
def related_posts(request, slug):
    try:
        current_post = Post.objects.get(slug=slug)
    except Post.DoesNotExist:
        raise NotFound('پست مورد نظر برای یافتن پست‌های مرتبط پیدا نشد.')

    paginator = CustomPageNumberPagination()
    tag_ids = current_post.tags.values_list('id', flat=True)
    if not tag_ids:
        return paginator.get_paginated_response([])

    related = Post.objects.filter(
        status='published',
        tags__in=tag_ids
    ).exclude(pk=current_post.pk).distinct()
    related = related.annotate(
        common_tags=Count('tags', filter=Q(tags__in=tag_ids))
    ).order_by('-common_tags', '-published_at', '-id')

    paginated_related_posts = paginator.paginate_queryset(related, request)
    serializer = PostListSerializer(paginated_related_posts, many=True, context={'request': request})
    return paginator.get_paginated_response(serializer.data)


class MediaViewSet(viewsets.ModelViewSet):
    queryset = Media.objects.all().order_by('-created_at')
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrAdmin]
    pagination_class = CustomPageNumberPagination
    ordering = ['-created_at']

    def get_queryset(self):
        return Media.objects.select_related('uploaded_by').all()

    def get_serializer_class(self):
        if self.action == 'create':
            return MediaCreateSerializer
        if self.action == 'finalize':
            return MediaFinalizeSerializer
        return MediaDetailSerializer

    def perform_create(self, serializer):
        uploaded_file = self.request.FILES.get('file')
        title = uploaded_file.name if uploaded_file else 'default_title'
        serializer.save(uploaded_by=self.request.user, title=title)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        # After creating, serialize with the detail serializer
        detail_serializer = MediaDetailSerializer(serializer.instance)
        headers = self.get_success_headers(detail_serializer.data)

        return Response(detail_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=False, methods=['post'])
    def initiate(self, request):
        """
        Initiates a file upload and returns a pre-signed URL (if using S3)
        or a temporary upload ID for local storage.
        """
        filename = request.data.get('filename')
        content_type = request.data.get('content_type')
        if not filename or not content_type:
            return Response(
                {'detail': 'filename and content_type are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate a unique key for the upload
        upload_id = f"tmp/{uuid.uuid4()}/{filename}"

        # If using S3, generate a pre-signed URL
        if hasattr(settings, 'AWS_STORAGE_BUCKET_NAME'):
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )
            try:
                url = s3_client.generate_presigned_url(
                    'put_object',
                    Params={
                        'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                        'Key': upload_id,
                        'ContentType': content_type
                    },
                    ExpiresIn=3600  # 1 hour
                )
                return Response({'upload_id': upload_id, 'upload_url': url})
            except ClientError as e:
                return Response({'detail': 'Could not generate upload URL.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            # For local storage, just return the upload_id.
            # The client will then upload to a separate endpoint handling the raw file.
            # This is a simplified flow for local dev. A better approach would be a dedicated upload handler.
            return Response({
                'upload_id': upload_id,
                'upload_url': '/api/media/upload-handler/' # A placeholder, would need a real handler
            })

    @action(detail=False, methods=['post'])
    def finalize(self, request):
        """
        Finalizes an upload after the file has been sent to storage by triggering
        an asynchronous task to process it.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Trigger the async task
        process_uploaded_media.delay(
            upload_id=data['upload_id'],
            user_id=request.user.id,
            title=data.get('title'),
            alt_text=data.get('alt_text')
        )

        return Response(
            {'detail': 'Upload received and is being processed.'},
            status=status.HTTP_202_ACCEPTED
        )


class AuthorProfileViewSet(viewsets.ModelViewSet):
    queryset = AuthorProfile.objects.all()
    serializer_class = AuthorProfileSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrAdmin]


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.select_related('parent').all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminUserOrReadOnly]


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAdminUserOrReadOnly]


class SeriesViewSet(viewsets.ModelViewSet):
    queryset = Series.objects.all()
    serializer_class = SeriesSerializer
    permission_classes = [IsAdminUserOrReadOnly]


class RevisionViewSet(viewsets.ModelViewSet):
    queryset = Revision.objects.all()
    serializer_class = RevisionSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrAdmin]


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()

        if user.is_authenticated and user.is_staff:
            return queryset

        if user.is_authenticated:
            return queryset.filter(
                Q(status='approved') | Q(user=user)
            ).distinct()

        return queryset.filter(status='approved')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        notify_author_on_new_comment.delay(serializer.instance.id)


class ReactionViewSet(viewsets.ModelViewSet):
    queryset = Reaction.objects.all()
    serializer_class = ReactionSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        queryset = super().get_queryset()

        user = self.request.user
        if user.is_authenticated and user.is_staff:
            return queryset

        return queryset.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PageViewSet(viewsets.ModelViewSet):
    queryset = Page.objects.all()
    serializer_class = PageSerializer
    permission_classes = [IsAdminUserOrReadOnly]


class MenuViewSet(viewsets.ModelViewSet):
    queryset = Menu.objects.all()
    serializer_class = MenuSerializer
    permission_classes = [IsAdminUserOrReadOnly]


class MenuItemViewSet(viewsets.ModelViewSet):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    permission_classes = [IsAdminUserOrReadOnly]


from django.http import FileResponse
from django.shortcuts import get_object_or_404
from .models import Media
from django.core.files.storage import default_storage

def download_media(request, media_id):
    media = get_object_or_404(Media, pk=media_id)
    file = default_storage.open(media.storage_key, 'rb')
    response = FileResponse(file, as_attachment=True, filename=media.title)
    return response

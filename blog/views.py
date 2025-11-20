from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import generics, status, viewsets
from rest_framework.decorators import api_view, permission_classes
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
from .permissions import IsOwnerOrReadOnly, IsAdminUserOrReadOnly
from .tasks import process_media_image, notify_author_on_new_comment
from .exceptions import custom_exception_handler
from rest_framework.views import APIView

class BaseBlogAPIView(APIView):
    def handle_exception(self, exc):
        """
        Handle any exception that occurs, by delegating to the custom exception handler.
        """
        return custom_exception_handler(exc, self.get_exception_handler_context())


class PostListCreateAPIView(generics.ListCreateAPIView):
    queryset = Post.objects.all().order_by('-published_at')
    pagination_class = CustomPageNumberPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = PostFilter
    search_fields = ['title', 'content', 'excerpt']
    ordering_fields = ['published_at', 'views_count']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PostCreateUpdateSerializer
        return PostListSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Post.objects.select_related('author', 'category') \
                               .prefetch_related('tags', 'reactions') \
                               .annotate(comments_count=Count('comments'))

        if user.is_authenticated and user.is_staff:
            return queryset
        if user.is_authenticated:
            return queryset.filter(
                Q(status='published', published_at__lte=timezone.now()) |
                Q(author__user=user, status__in=['draft', 'review'])
            ).distinct()
        return queryset.filter(status='published', published_at__lte=timezone.now())

    def perform_create(self, serializer):
        author_profile, _ = AuthorProfile.objects.get_or_create(
            user=self.request.user,
            defaults={'display_name': self.request.user.username}
        )
        serializer.save(author=author_profile)


class PostRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Post.objects.all()
    lookup_field = 'slug'

    def get_queryset(self):
        return Post.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return PostCreateUpdateSerializer
        return PostDetailSerializer

    def get_object(self):
        obj = super().get_object()
        if self.request.method == 'GET':
            obj.views_count += 1
            obj.save(update_fields=['views_count'])
        return obj


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsOwnerOrReadOnly])
def publish_post(request, slug):
    try:
        post = Post.objects.get(slug=slug)
    except Post.DoesNotExist:
        raise NotFound('پستی با این مشخصات یافت نشد.')

    # Check object-level permission
    if post.author.user != request.user and not request.user.is_staff:
        raise PermissionDenied('شما اجازه‌ی انتشار این پست را ندارید.')

    if post.status != 'draft':
        return Response(
            {'detail': 'تنها پست‌های پیش‌نویس را می‌توان منتشر کرد.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    post.status = 'published'
    post.published_at = timezone.now()
    post.save()
    serializer = PostDetailSerializer(post)
    return Response(serializer.data)


@api_view(['GET'])
def related_posts(request, slug):
    try:
        current_post = Post.objects.get(slug=slug)
    except Post.DoesNotExist:
        raise NotFound('پست مورد نظر برای یافتن پست‌های مرتبط پیدا نشد.')

    tag_ids = current_post.tags.values_list('id', flat=True)
    if not tag_ids:
        return Response([])

    related = Post.objects.filter(
        status='published',
        tags__in=tag_ids
    ).exclude(pk=current_post.pk).distinct()
    related = related.annotate(
        common_tags=Count('tags', filter=Q(tags__in=tag_ids))
    ).order_by('-common_tags', '-published_at')[:5]

    serializer = PostListSerializer(related, many=True)
    return Response(serializer.data)


class MediaViewSet(viewsets.ModelViewSet):
    queryset = Media.objects.all().order_by('-created_at')
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = CustomPageNumberPagination
    ordering = ['-created_at']

    def get_queryset(self):
        return Media.objects.select_related('uploaded_by').all()

    def get_serializer_class(self):
        if self.action == 'create':
            return MediaCreateSerializer
        return MediaDetailSerializer

    def perform_create(self, serializer):
        instance = serializer.save(uploaded_by=self.request.user)
        if 'image' in instance.mime:
            process_media_image.delay(instance.id)


class AuthorProfileViewSet(viewsets.ModelViewSet):
    queryset = AuthorProfile.objects.all()
    serializer_class = AuthorProfileSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
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
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

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
    permission_classes = [IsAuthenticated]

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

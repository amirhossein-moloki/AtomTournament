from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from .permissions import IsOwnerOrReadOnly, IsAdminUserOrReadOnly
from .models import (
    AuthorProfile, Category, Tag, Post, Series, Media, Revision,
    Comment, Reaction, Page, Menu, MenuItem
)
from .serializers import (
    AuthorProfileSerializer, CategorySerializer, TagSerializer,
    PostListSerializer, PostDetailSerializer,
    SeriesSerializer, MediaSerializer, RevisionSerializer, CommentSerializer,
    ReactionSerializer, PageSerializer, MenuSerializer, MenuItemSerializer
)
from .tasks import process_media_image, notify_author_on_new_comment


class MediaViewSet(viewsets.ModelViewSet):
    queryset = Media.objects.all()
    serializer_class = MediaSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        # Set the uploader to the current user
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


from django.db import models
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from .pagination import CustomCursorPagination
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.select_related('author', 'category').prefetch_related('tags').all()
    serializer_class = PostDetailSerializer # Default for create/update/retrieve
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    lookup_field = 'slug'
    pagination_class = CustomCursorPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'tags', 'status', 'author']
    search_fields = ['title', 'content', 'excerpt']
    ordering_fields = ['published_at', 'views_count', 'likes_count']

    def get_serializer_class(self):
        """Return different serializers for list and detail views."""
        if self.action == 'list':
            return PostListSerializer
        return PostDetailSerializer

    def get_queryset(self):
        """
        Dynamically filter queryset based on user role and post status.
        - Unauthenticated users: see only published posts.
        - Authenticated users: see published posts and their own drafts.
        - Admin users: see all posts.
        """
        user = self.request.user
        queryset = super().get_queryset()

        if user.is_authenticated and user.is_staff:
            return queryset  # Admin sees all

        # Authenticated users see published posts and their own drafts
        if user.is_authenticated:
            return queryset.filter(
                models.Q(status='published', published_at__lte=timezone.now()) |
                models.Q(author__user=user, status__in=['draft', 'review'])
            ).distinct()

        # Unauthenticated users see only published posts
        return queryset.filter(status='published', published_at__lte=timezone.now())

    def perform_create(self, serializer):
        """Set the author of the post to the current user."""
        try:
            author_profile = AuthorProfile.objects.get(user=self.request.user)
            serializer.save(author=author_profile)
        except AuthorProfile.DoesNotExist:
            # Handle cases where the user does not have an author profile
            # This might involve creating one or raising a validation error
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Authenticated user does not have an associated AuthorProfile.")

    @action(detail=True, methods=['post'], permission_classes=[IsOwnerOrReadOnly])
    def publish(self, request, pk=None):
        """
        Action to publish a draft post.
        """
        post = self.get_object()
        if post.status != 'draft':
            return Response({'error': 'Only draft posts can be published.'}, status=status.HTTP_400_BAD_REQUEST)

        post.status = 'published'
        post.published_at = timezone.now()
        post.save()
        return Response(self.get_serializer(post).data)

    @action(detail=True, methods=['get'], url_path='related', serializer_class=PostListSerializer)
    def related(self, request, slug=None):
        """
        Returns a list of related posts based on content similarity using TF-IDF.
        """
        try:
            current_post = self.get_object()
            published_posts = Post.objects.filter(status='published').exclude(pk=current_post.pk)

            if not published_posts.exists():
                return Response([])

            # Prepare documents for TF-IDF
            documents = [f"{post.title} {post.excerpt} {post.content}" for post in published_posts]
            current_document = f"{current_post.title} {current_post.excerpt} {current_post.content}"

            # Prepend the current post's document to the list to ensure it's part of the matrix
            documents.insert(0, current_document)

            # Create TF-IDF matrix
            vectorizer = TfidfVectorizer(stop_words='english', max_df=0.85, min_df=2)
            tfidf_matrix = vectorizer.fit_transform(documents)

            # Calculate cosine similarity between the current post and all others
            cosine_similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()

            # Get indices of the top 5 most similar posts
            # We add 1 to the indices because we are comparing with the matrix slice that excludes the first element
            related_indices = cosine_similarities.argsort()[-5:][::-1]

            # Get the actual Post objects
            related_posts = [published_posts[i] for i in related_indices]

            serializer = self.get_serializer(related_posts, many=True)
            return Response(serializer.data)
        except Post.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # Log the exception for debugging
            print(f"Error in related posts action: {e}")
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def get_queryset(self):
        """
        Filter comments based on status.
        - Approved comments are public.
        - Users can see their own pending comments.
        - Admins can see all comments.
        """
        user = self.request.user
        queryset = super().get_queryset()

        if user.is_authenticated and user.is_staff:
            return queryset

        if user.is_authenticated:
            return queryset.filter(
                models.Q(status='approved') |
                models.Q(user=user)
            ).distinct()

        return queryset.filter(status='approved')

    def perform_create(self, serializer):
        """
        Set the commenter to the current user and populate author details.
        """
        if self.request.user.is_authenticated:
            serializer.save(
                user=self.request.user,
                author_name=self.request.user.get_full_name() or self.request.user.username,
                author_email=self.request.user.email
            )
        else:
            # For anonymous users, name and email should be provided in the request
            serializer.save()

        notify_author_on_new_comment.delay(serializer.instance.id)


class ReactionViewSet(viewsets.ModelViewSet):
    queryset = Reaction.objects.all()
    serializer_class = ReactionSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

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

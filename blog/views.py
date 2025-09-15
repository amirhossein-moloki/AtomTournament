from datetime import timedelta
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import viewsets, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from .models import Post, Tag, Category, Comment, CommentReaction, CommentReport
from .serializers import (
    PostListSerializer,
    PostDetailSerializer,
    TagSerializer,
    CategorySerializer,
    CommentSerializer,
    CommentReportSerializer,
)
from .permissions import IsAuthorOrReadOnly


class PostViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]
    lookup_field = "slug"

    def get_serializer_class(self):
        if self.action == "list":
            return PostListSerializer
        return PostDetailSerializer

    def perform_create(self, serializer):
        slug = slugify(serializer.validated_data["title"])
        serializer.save(author=self.request.user, slug=slug)

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Post.objects.filter(
                Q(status="published")
                | (Q(status="draft") & Q(author=self.request.user))
            )
        return Post.objects.filter(status="published")


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    lookup_field = 'slug'


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'slug'


from rest_framework.decorators import action
from rest_framework.response import Response


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    filter_backends = [OrderingFilter, DjangoFilterBackend]
    ordering_fields = ['created_at', 'reactions_count']
    filterset_fields = ['parent']

    def get_queryset(self):
        return Comment.objects.filter(active=True, post__slug=self.kwargs.get('post_slug')).annotate(
            reactions_count=Count('reactions')
        )

    def perform_create(self, serializer):
        post = get_object_or_404(Post, slug=self.kwargs['post_slug'])
        serializer.save(author=self.request.user, post=post)

    def update(self, request, *args, **kwargs):
        comment = self.get_object()
        if timezone.now() > comment.created_at + timedelta(minutes=10):
            raise PermissionDenied("You can only edit comments within 10 minutes of posting.")
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def react(self, request, pk=None, post_slug=None):
        comment = self.get_object()
        user = request.user
        reaction_type = request.data.get("reaction_type")

        if not reaction_type:
            return Response(
                {"error": "Reaction type is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if reaction_type not in CommentReaction.ReactionType.values:
            return Response(
                {"error": "Invalid reaction type."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            existing_reaction = CommentReaction.objects.get(comment=comment, user=user)
            if existing_reaction.reaction_type == reaction_type:
                # User is removing their reaction
                existing_reaction.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                # User is changing their reaction
                existing_reaction.reaction_type = reaction_type
                existing_reaction.save()
                serializer = self.get_serializer(comment)
                return Response(serializer.data)
        except CommentReaction.DoesNotExist:
            # User is adding a new reaction
            CommentReaction.objects.create(
                comment=comment, user=user, reaction_type=reaction_type
            )
            serializer = self.get_serializer(comment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated], serializer_class=CommentReportSerializer)
    def report(self, request, pk=None, post_slug=None):
        comment = self.get_object()
        reporter = request.user

        if comment.author == reporter:
            return Response(
                {"error": "You cannot report your own comment."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save(comment=comment, reporter=reporter)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {"error": "You have already reported this comment."},
                status=status.HTTP_400_BAD_REQUEST,
            )

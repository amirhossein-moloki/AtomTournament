from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from rest_framework import viewsets, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Post, Tag, Category, Comment
from .serializers import (
    PostListSerializer,
    PostDetailSerializer,
    TagSerializer,
    CategorySerializer,
    CommentSerializer,
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


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.filter(active=True)
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        post = get_object_or_404(Post, slug=self.kwargs['post_slug'])
        serializer.save(author=self.request.user, post=post)

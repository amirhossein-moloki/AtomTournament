from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import (
    Post,
    Category,
    Tag,
    Comment,
    AuthorProfile,
    Media,
    Series,
    Reaction,
    Page,
    Revision,
    Menu,
    MenuItem,
    Role,
    Permission,
)
from .serializers import (
    PostSerializer,
    CategorySerializer,
    TagSerializer,
    CommentSerializer,
    AuthorProfileSerializer,
    MediaSerializer,
    SeriesSerializer,
    ReactionSerializer,
    PageSerializer,
    RevisionSerializer,
    MenuSerializer,
    MenuItemSerializer,
    RoleSerializer,
    PermissionSerializer,
)
from .tasks import increment_post_view_count, update_post_counts


class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.filter(status="published")
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["category", "tags", "author", "status", "visibility"]
    search_fields = ["title", "content", "excerpt"]
    ordering_fields = ["published_at", "views_count", "likes_count", "comments_count"]
    lookup_field = "slug"

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and user.is_staff:
            return Post.objects.all()
        if user.is_authenticated:
            return Post.objects.filter(status="published") | Post.objects.filter(author__user=user)
        return Post.objects.filter(status="published")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        increment_post_view_count.delay(instance.id)
        serializer = self.get_serializer(instance)
        return permissions.Response(serializer.data)

    def perform_create(self, serializer):
        author_profile = AuthorProfile.objects.get(user=self.request.user)
        serializer.save(author=author_profile)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = "slug"


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = "slug"


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.filter(status="approved")
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["post"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and user.is_staff:
            return Comment.objects.all()
        return Comment.objects.filter(status="approved")

    def perform_create(self, serializer):
        comment = serializer.save(user=self.request.user)
        update_post_counts.delay(comment.post.id)

    def perform_destroy(self, instance):
        post_id = instance.post.id
        instance.delete()
        update_post_counts.delay(post_id)


class AuthorProfileViewSet(viewsets.ModelViewSet):
    queryset = AuthorProfile.objects.all()
    serializer_class = AuthorProfileSerializer
    permission_classes = [permissions.IsAdminUser]


class MediaViewSet(viewsets.ModelViewSet):
    queryset = Media.objects.all()
    serializer_class = MediaSerializer
    permission_classes = [permissions.IsAdminUser]


class SeriesViewSet(viewsets.ModelViewSet):
    queryset = Series.objects.all()
    serializer_class = SeriesSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = "slug"


class ReactionViewSet(viewsets.ModelViewSet):
    queryset = Reaction.objects.all()
    serializer_class = ReactionSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        reaction = serializer.save(user=self.request.user)
        if reaction.content_type == "post":
            update_post_counts.delay(reaction.object_id)

    def perform_destroy(self, instance):
        post_id = instance.object_id if instance.content_type == "post" else None
        instance.delete()
        if post_id:
            update_post_counts.delay(post_id)


class PageViewSet(viewsets.ModelViewSet):
    queryset = Page.objects.all()
    serializer_class = PageSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = "slug"


class RevisionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Revision.objects.all()
    serializer_class = RevisionSerializer
    permission_classes = [permissions.IsAdminUser]


class MenuViewSet(viewsets.ModelViewSet):
    queryset = Menu.objects.all()
    serializer_class = MenuSerializer
    permission_classes = [permissions.IsAdminUser]


class MenuItemViewSet(viewsets.ModelViewSet):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    permission_classes = [permissions.IsAdminUser]


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAdminUser]


class PermissionViewSet(viewsets.ModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAdminUser]

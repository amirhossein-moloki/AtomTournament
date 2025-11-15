from rest_framework import viewsets
from .models import (
    AuthorProfile, Category, Tag, Post, Series, Media, Revision,
    Comment, Reaction, Page, Menu, MenuItem
)
from .serializers import (
    AuthorProfileSerializer, CategorySerializer, TagSerializer, PostSerializer,
    SeriesSerializer, MediaSerializer, RevisionSerializer, CommentSerializer,
    ReactionSerializer, PageSerializer, MenuSerializer, MenuItemSerializer
)
from .tasks import process_media_image, notify_author_on_new_comment


class MediaViewSet(viewsets.ModelViewSet):
    queryset = Media.objects.all()
    serializer_class = MediaSerializer

    def perform_create(self, serializer):
        instance = serializer.save()
        if 'image' in instance.mime:
            process_media_image.delay(instance.id)


class AuthorProfileViewSet(viewsets.ModelViewSet):
    queryset = AuthorProfile.objects.all()
    serializer_class = AuthorProfileSerializer


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer


class SeriesViewSet(viewsets.ModelViewSet):
    queryset = Series.objects.all()
    serializer_class = SeriesSerializer


class RevisionViewSet(viewsets.ModelViewSet):
    queryset = Revision.objects.all()
    serializer_class = RevisionSerializer


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer

    def perform_create(self, serializer):
        instance = serializer.save()
        notify_author_on_new_comment.delay(instance.id)


class ReactionViewSet(viewsets.ModelViewSet):
    queryset = Reaction.objects.all()
    serializer_class = ReactionSerializer


class PageViewSet(viewsets.ModelViewSet):
    queryset = Page.objects.all()
    serializer_class = PageSerializer


class MenuViewSet(viewsets.ModelViewSet):
    queryset = Menu.objects.all()
    serializer_class = MenuSerializer


class MenuItemViewSet(viewsets.ModelViewSet):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer

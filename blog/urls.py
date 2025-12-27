from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PostViewSet,
    related_posts,
    AuthorProfileViewSet, CategoryViewSet, TagViewSet, SeriesViewSet,
    MediaViewSet, RevisionViewSet, CommentViewSet, ReactionViewSet,
    PageViewSet, MenuViewSet, MenuItemViewSet,
    download_media
)

app_name = 'blog'

router = DefaultRouter()
router.register(r'posts', PostViewSet, basename='post')
router.register(r'authors', AuthorProfileViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'tags', TagViewSet)
router.register(r'series', SeriesViewSet)
router.register(r'media', MediaViewSet)
router.register(r'revisions', RevisionViewSet)
router.register(r'comments', CommentViewSet)
router.register(r'reactions', ReactionViewSet)
router.register(r'pages', PageViewSet)
router.register(r'menus', MenuViewSet)
router.register(r'menu-items', MenuItemViewSet)

urlpatterns = [
    path('posts/<slug:slug>/related/', related_posts, name='post-related'),
    path('media/<int:media_id>/download/', download_media, name='download_media'),
    path('', include(router.urls)),
]

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PostListCreateAPIView, PostRetrieveUpdateDestroyAPIView,
    publish_post, related_posts,
    AuthorProfileViewSet, CategoryViewSet, TagViewSet, SeriesViewSet,
    MediaViewSet, RevisionViewSet, CommentViewSet, ReactionViewSet,
    PageViewSet, MenuViewSet, MenuItemViewSet
)

router = DefaultRouter()
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
    path('posts/', PostListCreateAPIView.as_view(), name='post-list-create'),
    path('posts/<slug:slug>/', PostRetrieveUpdateDestroyAPIView.as_view(), name='post-detail'),
    path('posts/<slug:slug>/publish/', publish_post, name='post-publish'),
    path('posts/<slug:slug>/related/', related_posts, name='post-related'),
    path('', include(router.urls)),
]

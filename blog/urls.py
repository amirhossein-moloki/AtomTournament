from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AuthorProfileViewSet, CategoryViewSet, TagViewSet, PostViewSet, SeriesViewSet,
    MediaViewSet, RevisionViewSet, CommentViewSet, ReactionViewSet, PageViewSet,
    MenuViewSet, MenuItemViewSet
)

router = DefaultRouter()
router.register(r'author-profiles', AuthorProfileViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'tags', TagViewSet)
router.register(r'posts', PostViewSet)
router.register(r'series', SeriesViewSet)
router.register(r'media', MediaViewSet)
router.register(r'revisions', RevisionViewSet)
router.register(r'comments', CommentViewSet)
router.register(r'reactions', ReactionViewSet)
router.register(r'pages', PageViewSet)
router.register(r'menus', MenuViewSet)
router.register(r'menu-items', MenuItemViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

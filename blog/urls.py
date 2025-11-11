from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PostViewSet,
    CategoryViewSet,
    TagViewSet,
    CommentViewSet,
    AuthorProfileViewSet,
    MediaViewSet,
    SeriesViewSet,
    ReactionViewSet,
    PageViewSet,
    RevisionViewSet,
    MenuViewSet,
    MenuItemViewSet,
    RoleViewSet,
    PermissionViewSet,
)

router = DefaultRouter()
router.register(r"posts", PostViewSet)
router.register(r"categories", CategoryViewSet)
router.register(r"tags", TagViewSet)
router.register(r"comments", CommentViewSet)
router.register(r"authors", AuthorProfileViewSet)
router.register(r"media", MediaViewSet)
router.register(r"series", SeriesViewSet)
router.register(r"reactions", ReactionViewSet)
router.register(r"pages", PageViewSet)
router.register(r"revisions", RevisionViewSet)
router.register(r"menus", MenuViewSet)
router.register(r"menu-items", MenuItemViewSet)
router.register(r"roles", RoleViewSet)
router.register(r"permissions", PermissionViewSet)

urlpatterns = [
    path("", include(router.urls)),
]

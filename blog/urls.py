from rest_framework_nested import routers
from . import views

router = routers.SimpleRouter()
router.register(r'posts', views.PostViewSet, basename='post')
router.register(r'tags', views.TagViewSet, basename='tag')
router.register(r'categories', views.CategoryViewSet, basename='category')

posts_router = routers.NestedSimpleRouter(router, r'posts', lookup='post')
posts_router.register(r'comments', views.CommentViewSet, basename='post-comments')

urlpatterns = router.urls + posts_router.urls

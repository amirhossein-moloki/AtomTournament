from django_filters import rest_framework as filters
from .models import Post, Category, Tag

class PostFilter(filters.FilterSet):
    published_after = filters.DateTimeFilter(field_name="published_at", lookup_expr='gte')
    published_before = filters.DateTimeFilter(field_name="published_at", lookup_expr='lte')
    category = filters.CharFilter(field_name='category__slug')
    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
        conjoined=True,
    )

    class Meta:
        model = Post
        fields = ['series', 'visibility', 'published_after', 'published_before', 'category', 'tags']

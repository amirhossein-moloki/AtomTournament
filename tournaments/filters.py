import django_filters
from .models import Tournament


class TournamentFilter(django_filters.FilterSet):
    class Meta:
        model = Tournament
        fields = {
            "game": ["exact"],
            "type": ["exact"],
            "is_free": ["exact"],
            "start_date": ["gte", "lte"],
        }

import django_filters
from django.db.models import Q
from django.utils import timezone

from .models import Tournament


class TournamentFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr="icontains")
    status = django_filters.ChoiceFilter(
        choices=(
            ("upcoming", "Upcoming"),
            ("ongoing", "Ongoing"),
            ("finished", "Finished"),
            ("all", "All"),
        ),
        method="filter_by_status",
    )
    ordering = django_filters.OrderingFilter(
        fields=(
            ("name", "name"),
            ("start_date", "start_date"),
            ("entry_fee", "entry_fee"),
        )
    )

    class Meta:
        model = Tournament
        fields = {
            "game": ["exact"],
            "type": ["exact"],
            "is_free": ["exact"],
            "start_date": ["gte", "lte"],
        }

    def filter_by_status(self, queryset, name, value):
        now = timezone.now()
        if value == "upcoming":
            return queryset.filter(start_date__gt=now)
        elif value == "ongoing":
            return queryset.filter(start_date__lte=now, end_date__gte=now)
        elif value == "finished":
            return queryset.filter(end_date__lt=now)
        elif value == "all":
            return queryset
        return queryset

    @property
    def qs(self):
        parent_qs = super().qs
        status = self.data.get("status")
        if not status:
            return parent_qs.filter(end_date__gte=timezone.now())
        if status == "all":
            return parent_qs
        return parent_qs

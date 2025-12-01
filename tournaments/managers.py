from django.db import models
from django.utils import timezone


class TournamentQuerySet(models.QuerySet):
    def with_details(self, user=None):
        """
        Annotates the queryset with details like spots left, and user-specific
        information like rank and prize won if a user is provided.
        """
        # Annotate spots_left
        spots_left_annotation = models.Case(
            models.When(
                type='individual',
                then=models.F('max_participants') - models.Count('participants', distinct=True)
            ),
            models.When(
                type='team',
                then=models.F('max_participants') - models.Count('teams', distinct=True)
            ),
            default=models.Value(None),
            output_field=models.IntegerField()
        )
        queryset = self.annotate(spots_left=spots_left_annotation)

        # Annotate user-specific fields if authenticated
        if user and user.is_authenticated:
            from .models import Participant  # Avoid circular import
            participant_info = Participant.objects.filter(
                tournament=models.OuterRef('pk'),
                user=user
            )
            queryset = queryset.annotate(
                final_rank=models.Subquery(participant_info.values('rank')[:1]),
                prize_won=models.Subquery(participant_info.values('prize')[:1])
            )
        else:
            queryset = queryset.annotate(
                final_rank=models.Value(None, output_field=models.IntegerField()),
                prize_won=models.Value(None, output_field=models.DecimalField())
            )

        return queryset


class TournamentManager(models.Manager):
    def get_queryset(self):
        return TournamentQuerySet(self.model, using=self._db)

    def with_details(self, user=None):
        return self.get_queryset().with_details(user=user)

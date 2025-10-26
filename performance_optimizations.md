# Performance Optimizations

This document provides suggestions for optimizing the performance of the Django application.

## Query Optimization

### 1. `private_media_view` in `tournaments/views.py`

**Problem:** The `private_media_view` function has a potential N+1 query problem when checking team members' permissions.

**Original Code:**
```python
def private_media_view(request, path):
    try:
        match = Match.objects.get(result_proof=f"private_result_proofs/{path}")
    except Match.DoesNotExist:
        raise Http404

    is_participant = False
    if match.match_type == "individual":
        if request.user in [match.participant1_user, match.participant2_user]:
            is_participant = True
    else:
        if (
            request.user
            in [
                match.participant1_team.captain,
                match.participant2_team.captain,
            ]
            or request.user in match.participant1_team.members.all()
            or request.user in match.participant2_team.members.all()
        ):
            is_participant = True
```

**Optimized Code:**
```python
from django.db.models import Prefetch

def private_media_view(request, path):
    try:
        match = Match.objects.select_related(
            'participant1_team', 'participant2_team'
        ).prefetch_related(
            'participant1_team__members', 'participant2_team__members'
        ).get(result_proof=f"private_result_proofs/{path}")
    except Match.DoesNotExist:
        raise Http404

    is_participant = False
    if match.match_type == "individual":
        if request.user in [match.participant1_user, match.participant2_user]:
            is_participant = True
    else:
        if (
            request.user
            in [
                match.participant1_team.captain,
                match.participant2_team.captain,
            ]
            or request.user in match.participant1_team.members.all()
            or request.user in match.participant2_team.members.all()
        ):
            is_participant = True
```
**Explanation:** By using `select_related` for the teams and `prefetch_related` for the team members, we can fetch all the necessary data in a single query, avoiding the N+1 problem.

### 2. `WinnerSubmissionViewSet` in `tournaments/views.py`

**Problem:** The `get_queryset` method in `WinnerSubmissionViewSet` can cause an N+1 query when filtering by `tournament__creator`.

**Original Code:**
```python
def get_queryset(self):
    user = self.request.user
    if not user.is_authenticated:
        return WinnerSubmission.objects.none()

    queryset = WinnerSubmission.objects.all().select_related("winner", "tournament")

    if user.is_staff:
        return queryset

    queryset = queryset.filter(
        models.Q(winner=user) | models.Q(tournament__creator=user)
    ).distinct()

    return queryset
```

**Optimized Code:**
```python
def get_queryset(self):
    user = self.request.user
    if not user.is_authenticated:
        return WinnerSubmission.objects.none()

    queryset = WinnerSubmission.objects.select_related("winner", "tournament__creator")

    if user.is_staff:
        return queryset

    queryset = queryset.filter(
        models.Q(winner=user) | models.Q(tournament__creator=user)
    ).distinct()

    return queryset
```
**Explanation:** By using `select_related("winner", "tournament__creator")`, we can fetch the tournament creator along with the submission and tournament in a single query.

## Caching

### 1. Caching Top Tournaments

**Problem:** The `TopTournamentsView` queries the database for top tournaments every time it's accessed. This data is unlikely to change frequently.

**Suggestion:** Cache the results of the `TopTournamentsView` to reduce database load.

**Example Implementation:**
```python
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response

class TopTournamentsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        cached_data = cache.get('top_tournaments')
        if cached_data:
            return Response(cached_data)

        past_tournaments = Tournament.objects.filter(
            end_date__lt=timezone.now()
        ).order_by("-entry_fee")
        future_tournaments = Tournament.objects.filter(
            start_date__gte=timezone.now()
        ).order_by("-entry_fee")

        past_serializer = TournamentListSerializer(
            past_tournaments, many=True, context={"request": request}
        )
        future_serializer = TournamentListSerializer(
            future_tournaments, many=True, context={"request": request}
        )

        data = {
            "past_tournaments": past_serializer.data,
            "future_tournaments": future_serializer.data,
        }

        cache.set('top_tournaments', data, timeout=3600)  # Cache for 1 hour

        return Response(data)
```

### 2. Caching Total Prize Money and Tournament Count

**Problem:** The `TotalPrizeMoneyView` and `TotalTournamentsView` perform database queries that can be cached.

**Suggestion:** Cache the results of these views.

**Example Implementation:**
```python
class TotalPrizeMoneyView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        total_prize_money = cache.get('total_prize_money')
        if total_prize_money is None:
            total_prize_money = (
                Transaction.objects.filter(transaction_type="prize").aggregate(
                    total=models.Sum("amount")
                )["total"]
                or 0
            )
            cache.set('total_prize_money', total_prize_money, timeout=3600)
        return Response({"total_prize_money": total_prize_money})

class TotalTournamentsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        total_tournaments = cache.get('total_tournaments')
        if total_tournaments is None:
            total_tournaments = Tournament.objects.count()
            cache.set('total_tournaments', total_tournaments, timeout=3600)
        return Response({"total_tournaments": total_tournaments})
```

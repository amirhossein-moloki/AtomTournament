from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import (
    Case,
    CharField,
    F,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Cast, Coalesce, Concat, NullIf
from django.http import FileResponse, Http404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework.filters import OrderingFilter
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.tasks import send_tournament_credentials
from teams.models import Team
from teams.serializers import TeamSerializer
from users.models import User
from users.permissions import IsOwnerOrAdmin
from wallet.models import Transaction

from .exceptions import ApplicationError
from .api_mixins import DynamicFieldsMixin
from .filters import TournamentFilter
from .models import (Game, GameImage, Match, Participant, Report, Scoring,
                     Tournament, TournamentColor, TournamentImage,
                     WinnerSubmission)
from .permissions import (IsGameManagerOrAdmin, IsTournamentCreatorOrAdmin,
                          IsMatchParticipant)
from .serializers import (
    GameCreateUpdateSerializer,
    GameImageSerializer,
    GameReadOnlySerializer,
    MatchCreateSerializer,
    MatchReadOnlySerializer,
    MatchUpdateSerializer,
    ParticipantSerializer,
    ReportSerializer,
    ScoringSerializer,
    MatchSubmitResultSerializer,
    TournamentColorSerializer,
    TournamentCreateUpdateSerializer,
    TournamentImageSerializer,
    TournamentListSerializer,
    TournamentReadOnlySerializer,
    WinnerSubmissionSerializer,
    WinnerSubmissionCreateSerializer,
    TopTournamentsSerializer,
    TotalPrizeMoneySerializer,
    TotalTournamentsSerializer,
)
from .services import (approve_winner_submission_service, confirm_match_result,
                       create_report_service, create_winner_submission_service,
                       dispute_match_result, generate_matches, join_tournament,
                       reject_report_service, reject_winner_submission_service,
                       resolve_report_service)
from .tasks import generate_matches_task, approve_winner_submission_task
from common.throttles import (
    VeryStrictThrottle,
    StrictThrottle,
    MediumThrottle,
    RelaxedThrottle,
)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class TournamentParticipantListView(generics.ListAPIView):
    """
    API view to list participants of a tournament.
    """

    serializer_class = ParticipantSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """
        Optimized queryset to fetch participant data including the correct
        display picture URL in a single query.
        """
        tournament_id = self.kwargs["pk"]

        # Subquery to get the team picture URL for a participant's user
        # in the context of the participant's tournament.
        team_picture_subquery = Team.objects.filter(
            members=OuterRef("user_id"), tournaments=OuterRef("tournament_id")
        ).values("team_picture")[:1]

        # Expression to get the user's profile picture path,
        # replacing empty string with null.
        user_profile_picture = NullIf(
            Cast("user__profile_picture", CharField()), Value("")
        )

        # Expression to get the team picture path from the subquery,
        # replacing empty string with null.
        team_picture = NullIf(
            Subquery(team_picture_subquery, output_field=CharField()), Value("")
        )

        queryset = (
            Participant.objects.filter(tournament_id=tournament_id)
            .select_related("user", "tournament")
            .annotate(
                display_picture_url=Case(
                    When(
                        tournament__type="team",
                        then=Coalesce(
                            Concat(Value(settings.MEDIA_URL), team_picture),
                            Concat(Value(settings.MEDIA_URL), user_profile_picture),
                        ),
                    ),
                    default=Concat(Value(settings.MEDIA_URL), user_profile_picture),
                    output_field=CharField(),
                )
            )
        )
        return queryset


class TournamentViewSet(DynamicFieldsMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing tournaments.
    """

    queryset = Tournament.objects.all()
    lookup_field = 'slug'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['start_date', 'prize_pool', 'entry_fee']
    filterset_class = TournamentFilter
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.action == "list":
            return TournamentListSerializer
        if self.action in ["create", "update", "partial_update"]:
            return TournamentCreateUpdateSerializer
        return TournamentReadOnlySerializer

    def get_queryset(self):
        """
        Prefetch related data to optimize performance and avoid N+1 queries.
        """
        now = timezone.now()
        game_queryset_with_counts = Game.objects.annotate(
            held_tournaments_count=models.Count('tournament', filter=models.Q(tournament__end_date__lt=now)),
            active_tournaments_count=models.Count('tournament', filter=models.Q(tournament__end_date__gte=now))
        )
        team_picture_subquery = Team.objects.filter(
            members=OuterRef("user_id"), tournaments=OuterRef("tournament_id")
        ).values("team_picture")[:1]
        user_profile_picture = NullIf(
            Cast("user__profile_picture", CharField()), Value("")
        )
        team_picture = NullIf(
            Subquery(team_picture_subquery, output_field=CharField()), Value("")
        )
        participant_queryset = Participant.objects.select_related(
            "user", "tournament"
        ).annotate(
            display_picture_url=Case(
                When(
                    tournament__type="team",
                    then=Coalesce(
                        Concat(Value(settings.MEDIA_URL), team_picture),
                        Concat(Value(settings.MEDIA_URL), user_profile_picture),
                    ),
                ),
                default=Concat(Value(settings.MEDIA_URL), user_profile_picture),
                output_field=CharField(),
            )
        )

        queryset = (
            Tournament.objects.select_related("image", "color", "creator", "game")
            .prefetch_related(
                Prefetch("participant_set", queryset=participant_queryset),
                "participants",  # Added for direct access in serializer
                "teams",
            )
        )

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
        queryset = queryset.annotate(spots_left=spots_left_annotation)

        # Annotate user-specific fields if authenticated
        user = self.request.user
        if user and user.is_authenticated:
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

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        if self.action in [
            "create",
            "update",
            "partial_update",
            "destroy",
            "generate_matches",
            "start_countdown",
        ]:
            return [IsGameManagerOrAdmin()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    def get_throttles(self):
        if self.action == 'join':
            self.throttle_classes = [StrictThrottle]
        elif self.action in ['list', 'retrieve']:
            self.throttle_classes = [MediumThrottle]
        else:
            self.throttle_classes = [RelaxedThrottle]
        return super().get_throttles()

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def join(self, request, pk=None):
        """
        Join a tournament.
        """
        tournament = self.get_object()
        user = request.user
        team_id = request.data.get("team_id")
        member_ids = request.data.get("member_ids")

        try:
            result = join_tournament(
                tournament=tournament,
                user=user,
                team_id=team_id,
                member_ids=member_ids,
            )
            if tournament.type == "individual":
                serializer = ParticipantSerializer(result)
            else:
                serializer = TeamSerializer(result)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ApplicationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminUser])
    def generate_matches(self, request, pk=None):
        """
        Generate matches for a tournament.
        """
        tournament = self.get_object()
        try:
            generate_matches_task.delay(tournament.id)
            return Response({"message": "Match generation has been started."})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminUser])
    def start_countdown(self, request, pk=None):
        """
        Start the countdown for a tournament.
        """
        tournament = self.get_object()
        tournament.countdown_start_time = timezone.now()
        tournament.save()
        send_tournament_credentials.apply_async(
            (tournament.id,),
            eta=tournament.countdown_start_time + timezone.timedelta(minutes=5),
        )
        return Response({"message": "Countdown started."})


class MatchViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing matches.
    """
    parser_classes = (MultiPartParser, FormParser)

    queryset = Match.objects.all().select_related(
        "tournament",
        "participant1_user",
        "participant2_user",
        "participant1_team",
        "participant2_team",
        "winner_user",
        "winner_team",
    ).prefetch_related(
        "participant1_team__members",
        "participant2_team__members",
        "winner_team__members",
    )

    def get_serializer_class(self):
        if self.action == "create":
            return MatchCreateSerializer
        if self.action in ["update", "partial_update"]:
            return MatchUpdateSerializer
        return MatchReadOnlySerializer

    def get_permissions(self):
        if self.request.user and self.request.user.is_staff:
            return [IsAdminUser()]
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        if self.action in ["create", "destroy"]:
            return [IsAdminUser()]
        if self.action in ["update", "partial_update"]:
            return [IsMatchParticipant()]
        return [IsAuthenticated()]

    def get_throttles(self):
        if self.action in ['confirm_result', 'dispute_result']:
            self.throttle_classes = [StrictThrottle]
        elif self.action in ['list', 'retrieve']:
            self.throttle_classes = [MediumThrottle]
        else:
            self.throttle_classes = [RelaxedThrottle]
        return super().get_throttles()

    @action(detail=True, methods=["post"], permission_classes=[IsMatchParticipant], parser_classes=[MultiPartParser, FormParser])
    def submit_result(self, request, pk=None):
        """
        Submit the result of a match by one of its participants.
        """
        match = self.get_object()
        user = request.user

        if match.status != "ongoing":
            return Response({"error": "این مسابقه در وضعیت 'در حال برگزاری' قرار ندارد."}, status=status.HTTP_400_BAD_REQUEST)

        if match.result_submitted_by is not None:
            return Response({"error": "نتیجه این مسابقه قبلاً ثبت شده است."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = MatchSubmitResultSerializer(data=request.data)
        if serializer.is_valid():
            winner_id = serializer.validated_data['winner_id']
            result_proof = serializer.validated_data['result_proof']

            if match.match_type == 'individual':
                if winner_id not in [match.participant1_user_id, match.participant2_user_id]:
                     return Response({"error": "شناسه برنده نامعتبر است."}, status=status.HTTP_400_BAD_REQUEST)
                try:
                    winner_user = User.objects.get(id=winner_id)
                    match.winner_user = winner_user
                except User.DoesNotExist:
                    return Response({"error": "کاربر برنده یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
            else:
                if winner_id not in [match.participant1_team_id, match.participant2_team_id]:
                     return Response({"error": "شناسه تیم برنده نامعتبر است."}, status=status.HTTP_400_BAD_REQUEST)
                try:
                    winner_team = Team.objects.get(id=winner_id)
                    match.winner_team = winner_team
                except Team.DoesNotExist:
                    return Response({"error": "تیم برنده یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

            match.result_proof = result_proof
            match.result_submitted_by = user
            match.status = "pending_confirmation"
            match.save()

            return Response(MatchReadOnlySerializer(match, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], permission_classes=[IsMatchParticipant])
    def confirm_result(self, request, pk=None):
        """
        Confirm the match result submitted by the other participant.
        """
        match = self.get_object()
        user = request.user

        if match.status != "pending_confirmation":
            return Response({"error": "این مسابقه در وضعیت 'در انتظار تایید' قرار ندارد."}, status=status.HTTP_400_BAD_REQUEST)

        if match.result_submitted_by == user:
            return Response({"error": "شما نمی‌توانید نتیجه‌ای که خودتان ثبت کرده‌اید را تایید کنید."}, status=status.HTTP_400_BAD_REQUEST)

        match.is_confirmed = True
        match.status = "completed"
        match.save()

        return Response(MatchReadOnlySerializer(match, context={'request': request}).data)

    @action(detail=True, methods=["post"], permission_classes=[IsMatchParticipant])
    def dispute_result(self, request, pk=None):
        """
        Dispute the match result submitted by the other participant.
        """
        match = self.get_object()
        user = request.user
        reason = request.data.get("reason")

        if not reason:
            return Response({"error": "دلیل اعتراض باید مشخص شود."}, status=status.HTTP_400_BAD_REQUEST)

        if match.status != "pending_confirmation":
            return Response({"error": "این مسابقه در وضعیت 'در انتظار تایید' قرار ندارد."}, status=status.HTTP_400_BAD_REQUEST)

        if match.result_submitted_by == user:
            return Response({"error": "شما نمی‌توانید به نتیجه‌ای که خودتان ثبت کرده‌اید اعتراض کنید."}, status=status.HTTP_400_BAD_REQUEST)

        match.is_disputed = True
        match.status = "disputed"
        match.dispute_reason = reason
        match.save()

        return Response(MatchReadOnlySerializer(match, context={'request': request}).data)

class GameViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing games.
    """
    pagination_class = StandardResultsSetPagination
    lookup_field = 'slug'

    def get_queryset(self):
        now = timezone.now()
        return Game.objects.all().prefetch_related("images").annotate(
            status_order=Case(
                When(status='active', then=1),
                When(status='coming_soon', then=2),
                When(status='inactive', then=3),
                default=4,
                output_field=models.IntegerField(),
            ),
            held_tournaments_count=models.Count(
                'tournament', filter=models.Q(tournament__end_date__lt=now)
            ),
            active_tournaments_count=models.Count(
                'tournament', filter=models.Q(tournament__end_date__gte=now)
            )
        ).order_by('status_order')

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return GameCreateUpdateSerializer
        return GameReadOnlySerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAdminUser()]
        return [IsAuthenticated()]


class GameImageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing game images.
    """

    queryset = GameImage.objects.select_related("game")
    serializer_class = GameImageSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAdminUser()]


class TournamentImageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing tournament images.
    """

    queryset = TournamentImage.objects.all()
    serializer_class = TournamentImageSerializer
    permission_classes = [IsAdminUser]


class TournamentColorViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing tournament colors.
    """

    queryset = TournamentColor.objects.all()
    serializer_class = TournamentColorSerializer
    permission_classes = [IsAdminUser]


@extend_schema(
    responses={
        200: OpenApiResponse(description="File content"),
        403: OpenApiResponse(description="Permission denied"),
        404: OpenApiResponse(description="File not found"),
    }
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def private_media_view(request, path):
    """
    This view serves private media files. It requires authentication and
    checks if the user is a participant in the match to which the file
    belongs.
    """
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

    if is_participant or request.user.is_staff:
        response = Response(status=status.HTTP_200_OK)
        response["X-Accel-Redirect"] = f"/protected_media/{path}"
        response["Content-Type"] = ""  # Let Nginx determine the content type
        return response
    else:
        return Response(
            {"error": "You do not have permission to access this file."},
            status=status.HTTP_403_FORBIDDEN,
        )


class ReportViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing reports.
    """

    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        queryset = Report.objects.all().select_related(
            "reporter", "reported_user", "match", "tournament"
        )
        if not self.request.user.is_staff:
            queryset = queryset.filter(reporter=self.request.user)
        return queryset

    def perform_create(self, serializer):
        validated_data = serializer.validated_data
        create_report_service(
            reporter=self.request.user,
            reported_user_id=validated_data["reported_user"].id,
            tournament=validated_data["tournament"],
            match=validated_data.get("match"),
            description=validated_data["description"],
            evidence=validated_data.get("evidence"),
        )

    @action(detail=True, methods=["post"], permission_classes=[IsAdminUser])
    def resolve(self, request, pk=None):
        """
        Resolve a report and ban the reported user if necessary.
        """
        report = self.get_object()
        ban_user = request.data.get("ban_user", False)
        resolve_report_service(report, ban_user)
        message = "Report resolved and user banned." if ban_user else "Report resolved."
        return Response({"message": message})

    @action(detail=True, methods=["post"], permission_classes=[IsAdminUser])
    def reject(self, request, pk=None):
        """
        Reject a report.
        """
        report = self.get_object()
        reject_report_service(report)
        return Response({"message": "Report rejected."})


class WinnerSubmissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing winner submissions.
    """

    queryset = WinnerSubmission.objects.all()
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def get_serializer_class(self):
        if self.action == 'create':
            return WinnerSubmissionCreateSerializer
        return WinnerSubmissionSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return WinnerSubmission.objects.none()

        queryset = WinnerSubmission.objects.all().select_related("winner", "tournament")

        if user.is_staff:
            return queryset

        # Allow winner to see their own submissions
        # Allow tournament creator to see submissions for their tournament
        queryset = queryset.filter(
            models.Q(winner=user) | models.Q(tournament__creator=user)
        ).distinct()

        return queryset

    def perform_create(self, serializer):
        create_winner_submission_service(
            user=self.request.user,
            tournament=serializer.validated_data["tournament"],
            image=serializer.validated_data["image"],
        )

    @action(detail=True, methods=["post"], permission_classes=[IsTournamentCreatorOrAdmin])
    def approve(self, request, pk=None):
        """
        Approve a winner submission and pay the prize.
        """
        submission = self.get_object()
        approve_winner_submission_task.delay(submission.id)
        return Response({"message": "Submission approval process has been started."})

    @action(detail=True, methods=["post"], permission_classes=[IsTournamentCreatorOrAdmin])
    def reject(self, request, pk=None):
        """
        Reject a winner submission.
        """
        submission = self.get_object()
        reject_winner_submission_service(submission)
        return Response({"message": "Submission rejected and entry fees refunded."})


class AdminReportListView(generics.ListAPIView):
    """
    API view for admin to see all reports.
    """

    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [IsAdminUser]


class AdminWinnerSubmissionListView(generics.ListAPIView):
    """
    API view for admin to see all winner submissions.
    """

    queryset = WinnerSubmission.objects.all()
    serializer_class = WinnerSubmissionSerializer
    permission_classes = [IsAdminUser]


class ScoringViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing scores.
    """



    queryset = Scoring.objects.all().select_related("tournament", "user")
    serializer_class = ScoringSerializer
    permission_classes = [IsAdminUser]


@extend_schema(responses=TopTournamentsSerializer)
class TopTournamentsView(APIView):
    """
    API view for getting top tournaments by prize pool.
    """

    permission_classes = [AllowAny]

    @method_decorator(cache_page(60 * 15))
    def get(self, request):
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

        return Response(
            {
                "past_tournaments": past_serializer.data,
                "future_tournaments": future_serializer.data,
            }
        )


@extend_schema(responses=TotalPrizeMoneySerializer)
class TotalPrizeMoneyView(APIView):
    """
    API view for getting the total prize money paid out.
    """

    permission_classes = [AllowAny]

    @method_decorator(cache_page(60 * 15))
    def get(self, request):
        total_prize_money = (
            Transaction.objects.filter(transaction_type="prize").aggregate(
                total=models.Sum("amount")
            )["total"]
            or 0
        )
        return Response({"total_prize_money": total_prize_money})


@extend_schema(responses=TotalTournamentsSerializer)
class TotalTournamentsView(APIView):
    """
    API view for getting the total number of tournaments held.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        total_tournaments = Tournament.objects.count()
        return Response({"total_tournaments": total_tournaments})


class UserTournamentHistoryView(generics.ListAPIView):
    """
    API view to list tournaments a user has participated in.
    """

    serializer_class = TournamentListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        This view should return a list of all the tournaments
        for the currently authenticated user.
        """
        user = self.request.user
        now = timezone.now()
        game_queryset_with_counts = Game.objects.annotate(
            held_tournaments_count=models.Count('tournament', filter=models.Q(tournament__end_date__lt=now)),
            active_tournaments_count=models.Count('tournament', filter=models.Q(tournament__end_date__gte=now))
        )
        participant_queryset = Participant.objects.select_related("user")
        queryset = Tournament.objects.filter(participants=user).prefetch_related(
            Prefetch("participant_set", queryset=participant_queryset),
            "teams",
            Prefetch("game", queryset=game_queryset_with_counts)
        )

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
        queryset = queryset.annotate(spots_left=spots_left_annotation)

        # Annotate user-specific fields
        participant_info = Participant.objects.filter(
            tournament=models.OuterRef('pk'),
            user=user
        )
        queryset = queryset.annotate(
            final_rank=models.Subquery(participant_info.values('rank')[:1]),
            prize_won=models.Subquery(participant_info.values('prize')[:1])
        )

        return queryset

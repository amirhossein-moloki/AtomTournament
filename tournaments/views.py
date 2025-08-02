import os
from django.conf import settings
from django.http import FileResponse, Http404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from django.db import models
from django.db.models import Prefetch
from wallet.models import Transaction
from django.core.exceptions import ValidationError
from rest_framework import generics, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from users.serializers import TeamSerializer
from .exceptions import ApplicationError
from .filters import TournamentFilter
from .permissions import IsTournamentManagerOrAdmin
from django_filters.rest_framework import DjangoFilterBackend

from .models import Game, Match, Tournament, Participant
from .serializers import (
    GameSerializer,
    MatchSerializer,
    TournamentSerializer,
    ParticipantSerializer,
)
from notifications.tasks import send_tournament_credentials
from .services import (
    join_tournament,
    generate_matches,
    confirm_match_result,
    dispute_match_result,
    create_report_service,
    resolve_report_service,
    reject_report_service,
    create_winner_submission_service,
    approve_winner_submission_service,
    reject_winner_submission_service,
)
from .models import Report, WinnerSubmission
from .serializers import ReportSerializer, WinnerSubmissionSerializer, ScoringSerializer
from .models import Scoring


class TournamentParticipantListView(generics.ListAPIView):
    """
    API view to list participants of a tournament.
    """

    serializer_class = ParticipantSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tournament_id = self.kwargs["pk"]
        return Participant.objects.filter(tournament_id=tournament_id)


class TournamentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing tournaments.
    """

    serializer_class = TournamentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Prefetch related data to optimize performance and avoid N+1 queries.
        - `participant_set` is needed by the serializer to get user-specific rank and prize.
        - `teams` and `game` are also serialized.
        """
        participant_queryset = Participant.objects.select_related('user')
        return Tournament.objects.prefetch_related(
            Prefetch('participant_set', queryset=participant_queryset),
            'teams',
            'game'
        ).all()
    filter_backends = [DjangoFilterBackend]
    filterset_class = TournamentFilter

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy', 'generate_matches', 'start_countdown']:
            return [IsTournamentManagerOrAdmin()]
        if self.action == 'create':
            return [IsAdminUser()]
        return [IsAuthenticated()]

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
            generate_matches(tournament)
            return Response({"message": "Matches generated successfully."})
        except ValidationError as e:
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
            (tournament.id,), eta=tournament.countdown_start_time + timezone.timedelta(minutes=5)
        )
        return Response({"message": "Countdown started."})


class MatchViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing matches.
    """

    queryset = Match.objects.all()
    serializer_class = MatchSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ["create", "destroy"]:
            return [IsAdminUser()]
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def confirm_result(self, request, pk=None):
        """
        Confirm the result of a match.
        """
        match = self.get_object()
        winner_id = request.data.get("winner_id")

        if not winner_id:
            return Response({"error": "Winner ID not provided."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            confirm_match_result(match, requesting_user=request.user, winner_id=winner_id)
            return Response({"message": "Match result confirmed successfully."})
        except (ApplicationError, PermissionDenied, ValidationError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def dispute_result(self, request, pk=None):
        """
        Dispute the result of a match.
        """
        match = self.get_object()
        user = request.user
        reason = request.data.get("reason")

        if not reason:
            return Response(
                {"error": "Reason for dispute not provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            dispute_match_result(match, user, reason)
            return Response({"message": "Match result disputed successfully."})
        except (PermissionDenied, ValidationError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GameViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing games.
    """

    queryset = Game.objects.all()
    serializer_class = GameSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAdminUser()]
        return super().get_permissions()


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
        if request.user in [
            match.participant1_team.captain,
            match.participant2_team.captain,
        ] or request.user in match.participant1_team.members.all() or request.user in match.participant2_team.members.all():
            is_participant = True

    if is_participant or request.user.is_staff:
        safe_base_path = os.path.abspath(settings.PRIVATE_MEDIA_ROOT)
        requested_path = os.path.abspath(os.path.join(safe_base_path, path))

        if not requested_path.startswith(safe_base_path) or not os.path.exists(
            requested_path
        ):
            raise Http404

        return FileResponse(open(requested_path, "rb"))
    else:
        return Response(
            {"error": "You do not have permission to access this file."}, status=403
        )


class ReportViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing reports.
    """

    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Report.objects.all()
        return Report.objects.filter(reporter=self.request.user)

    def perform_create(self, serializer):
        validated_data = serializer.validated_data
        create_report_service(
            reporter=self.request.user,
            reported_user_id=validated_data["reported_user"].id,
            match_id=validated_data["match"].id,
            description=validated_data["description"],
            evidence=validated_data.get("evidence")
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
    serializer_class = WinnerSubmissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return WinnerSubmission.objects.all()
        return WinnerSubmission.objects.filter(winner=self.request.user)

    def perform_create(self, serializer):
        if not serializer.is_valid():
            print("Serializer errors:", serializer.errors)
        validated_data = serializer.validated_data
        try:
            create_winner_submission_service(
                user=self.request.user,
                tournament=validated_data["tournament"],
                video=validated_data["video"]
            )
        except ApplicationError as e:
            # DRF's exception handler will turn this into a 400 response
            raise ValidationError(str(e))

    @action(detail=True, methods=["post"], permission_classes=[IsAdminUser])
    def approve(self, request, pk=None):
        """
        Approve a winner submission and pay the prize.
        """
        submission = self.get_object()
        approve_winner_submission_service(submission)
        return Response({"message": "Submission approved and prize paid."})

    @action(detail=True, methods=["post"], permission_classes=[IsAdminUser])
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

    queryset = Scoring.objects.all()
    serializer_class = ScoringSerializer
    permission_classes = [IsAdminUser]


class TopTournamentsView(APIView):
    """
    API view for getting top tournaments by prize pool.
    """

    def get(self, request):
        past_tournaments = (
            Tournament.objects.filter(end_date__lt=timezone.now())
            .order_by("-entry_fee")
        )
        future_tournaments = (
            Tournament.objects.filter(start_date__gte=timezone.now())
            .order_by("-entry_fee")
        )

        past_serializer = TournamentSerializer(past_tournaments, many=True)
        future_serializer = TournamentSerializer(future_tournaments, many=True)

        return Response(
            {
                "past_tournaments": past_serializer.data,
                "future_tournaments": future_serializer.data,
            }
        )


class TotalPrizeMoneyView(APIView):
    """
    API view for getting the total prize money paid out.
    """

    def get(self, request):
        total_prize_money = (
            Transaction.objects.filter(transaction_type="prize").aggregate(
                total=models.Sum("amount")
            )["total"]
            or 0
        )
        return Response({"total_prize_money": total_prize_money})


class TotalTournamentsView(APIView):
    """
    API view for getting the total number of tournaments held.
    """

    def get(self, request):
        total_tournaments = Tournament.objects.count()
        return Response({"total_tournaments": total_tournaments})


class UserTournamentHistoryView(generics.ListAPIView):
    """
    API view to list tournaments a user has participated in.
    """

    serializer_class = TournamentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        This view should return a list of all the tournaments
        for the currently authenticated user.
        """
        user = self.request.user
        return Tournament.objects.filter(participants=user)

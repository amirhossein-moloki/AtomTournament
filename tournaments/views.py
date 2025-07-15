from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from django.core.exceptions import PermissionDenied, ValidationError
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from .models import Game, Match, Tournament
from .serializers import (
    GameSerializer,
    MatchSerializer,
    TournamentSerializer,
    ParticipantSerializer,
)
from .services import join_tournament, generate_matches


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

    queryset = Tournament.objects.all()
    serializer_class = TournamentSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ["create", "destroy"]:
            return [IsAdminUser()]
        return super().get_permissions()

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def join(self, request, pk=None):
        """
        Join a tournament.
        """
        tournament = self.get_object()
        user = request.user

        if tournament.type == "team" and not user.team:
            return Response(
                {"error": "You must be in a team to join this tournament."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            participant = join_tournament(tournament, user)
            serializer = ParticipantSerializer(participant)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
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
        user = request.user
        winner_id = request.data.get("winner_id")

        if not winner_id:
            return Response(
                {"error": "Winner ID not provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            confirm_match_result(match, user, winner_id)
            return Response({"message": "Match result confirmed successfully."})
        except (PermissionDenied, ValidationError) as e:
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
        file_path = f"{settings.PRIVATE_MEDIA_ROOT}/{path}"
        return FileResponse(open(file_path, "rb"))
    else:
        return Response(
            {"error": "You do not have permission to access this file."}, status=403
        )

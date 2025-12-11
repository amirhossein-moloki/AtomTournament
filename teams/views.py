from django.core.exceptions import ValidationError
from django.db import models
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tournaments.models import Match
from tournaments.serializers import MatchReadOnlySerializer

from .models import Team, TeamInvitation, TeamMembership
from .permissions import IsCaptain, IsCaptainOrReadOnly, IsTeamMemberOrAdmin
from .serializers import (
    TeamInvitationSerializer,
    TeamSerializer,
    TopTeamSerializer,
)
from .services import (
    ApplicationError,
    invite_member_service,
    leave_team_service,
    remove_member_service,
    respond_to_invitation_service,
)


class TeamViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing teams.
    """

    queryset = Team.objects.all().select_related("captain").prefetch_related("members")
    serializer_class = TeamSerializer
    permission_classes = [IsCaptainOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["name", "captain"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticated()]
        return super().get_permissions()

    def perform_create(self, serializer):
        team = serializer.save(captain=self.request.user)
        TeamMembership.objects.create(user=self.request.user, team=team)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsCaptain],
        url_path="add-member",
    )
    def invite_member(self, request, pk=None):
        """
        Invite a member to a team.
        """
        team = self.get_object()
        user_id = request.data.get("user_id")
        if not user_id:
            return Response(
                {"error": "User ID is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            invite_member_service(team=team, from_user=request.user, to_user_id=user_id)
            return Response(
                {"message": "Invitation sent successfully."}, status=status.HTTP_200_OK
            )
        except ApplicationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"], permission_classes=[IsTeamMemberOrAdmin], url_path="match-history")
    def match_history(self, request, pk=None):
        """
        Return the match history for the team.
        """
        team = self.get_object()

        queryset = Match.objects.filter(
            models.Q(participant1_team=team) | models.Q(participant2_team=team)
        ).distinct()

        serializer = MatchReadOnlySerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],
        url_path="invitations",
    )
    def invitations(self, request):
        """
        List all pending invitations for the current user.
        """
        invitations = TeamInvitation.objects.filter(
            to_user=request.user, status="pending"
        )
        serializer = TeamInvitationSerializer(invitations, many=True)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[IsAuthenticated],
        url_path="respond-invitation",
    )
    def respond_invitation(self, request):
        """
        Respond to a team invitation.
        """
        invitation_id = request.data.get("invitation_id")
        status_action = request.data.get("status")
        if not invitation_id or not status_action:
            return Response(
                {"error": "Invitation ID and status are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            respond_to_invitation_service(
                invitation_id=invitation_id, user=request.user, status=status_action
            )
            return Response(
                {"message": f"Invitation {status_action}."}, status=status.HTTP_200_OK
            )
        except (ApplicationError, ValidationError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def leave_team(self, request, pk=None):
        """
        Leave a team.
        """
        team = self.get_object()
        try:
            leave_team_service(team=team, user=request.user)
            return Response(
                {"message": "You have left the team."}, status=status.HTTP_200_OK
            )
        except ApplicationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], permission_classes=[IsCaptain])
    def remove_member(self, request, pk=None):
        """
        Remove a member from a team.
        """
        team = self.get_object()
        user_id = request.data.get("user_id")
        if not user_id:
            return Response(
                {"error": "User ID is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            remove_member_service(team=team, captain=request.user, member_id=user_id)
            return Response(
                {"message": "Member removed successfully."}, status=status.HTTP_200_OK
            )
        except ApplicationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(responses=TopTeamSerializer(many=True))
class TopTeamsView(APIView):
    """
    API view for getting top teams by prize money.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        teams = Team.objects.annotate(
            total_winnings=models.Sum(
                "members__wallet__transactions__amount",
                filter=models.Q(members__wallet__transactions__transaction_type="prize"),
            )
        ).order_by("-total_winnings")
        serializer = TopTeamSerializer(teams, many=True)
        return Response(serializer.data)



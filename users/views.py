from django.db import models
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_ratelimit.decorators import ratelimit
from rest_framework.response import Response
from django.db.models import Prefetch
from wallet.models import Transaction

from .services import (
    send_otp_service,
    verify_otp_service,
    ApplicationError,
    invite_member_service,
    respond_to_invitation_service,
    leave_team_service,
    remove_member_service,
)
from .models import Role, Team, User, TeamInvitation
from .permissions import IsAdminUser, IsCaptain, IsCaptainOrReadOnly, IsOwnerOrReadOnly
from .serializers import (
    RoleSerializer,
    TeamSerializer,
    UserSerializer,
    TeamInvitationSerializer,
    TopPlayerSerializer,
    TopTeamSerializer,
)
from wallet.serializers import TransactionSerializer
from tournaments.serializers import TournamentSerializer
from rest_framework.views import APIView
from tournaments.models import Tournament


class RoleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing roles.
    """

    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAdminUser]


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing users.
    """

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["username", "email"]

    def get_permissions(self):
        if self.action in ["create", "send_otp", "verify_otp"]:
            return [AllowAny()]
        return super().get_permissions()

    @action(detail=True, methods=["get"])
    def tournaments(self, request, pk=None):
        user = self.get_object()
        tournaments = Tournament.objects.filter(participants=user)
        serializer = TournamentSerializer(tournaments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def send_otp(self, request):
        """
        Send OTP to user.
        """
        phone_number = request.data.get("phone_number")
        email = request.data.get("email")
        try:
            send_otp_service(phone_number=phone_number, email=email)
            return Response(
                {"message": "OTP sent successfully."}, status=status.HTTP_200_OK
            )
        except ApplicationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def verify_otp(self, request):
        """
        Verify OTP and login user.
        """
        phone_number = request.data.get("phone_number")
        email = request.data.get("email")
        code = request.data.get("code")
        try:
            tokens = verify_otp_service(
                phone_number=phone_number, email=email, code=code
            )
            return Response(tokens, status=status.HTTP_200_OK)
        except ApplicationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class TeamViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing teams.
    """

    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    permission_classes = [IsAuthenticated, IsCaptainOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["name", "captain"]

    def perform_create(self, serializer):
        serializer.save(captain=self.request.user)

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
        except ApplicationError as e:
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


class DashboardView(APIView):
    """
    API view for user dashboard.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = User.objects.prefetch_related(
            Prefetch(
                "tournaments",
                queryset=Tournament.objects.filter(
                    start_date__gte=timezone.now()
                ).order_by("start_date"),
            ),
            Prefetch(
                "sent_invitations",
                queryset=TeamInvitation.objects.filter(status="pending"),
            ),
            Prefetch(
                "received_invitations",
                queryset=TeamInvitation.objects.filter(status="pending"),
            ),
            Prefetch(
                "wallet__transaction_set",
                queryset=Transaction.objects.order_by("-timestamp")[:5],
            ),
        ).get(pk=request.user.pk)

        # The data is now pre-fetched, so accessing it doesn't cause new queries.
        upcoming_tournaments = user.tournaments.all()
        sent_invitations = user.sent_invitations.all()
        received_invitations = user.received_invitations.all()
        latest_transactions = user.wallet.transaction_set.all()

        data = {
            "upcoming_tournaments": TournamentSerializer(
                upcoming_tournaments, many=True, context={"request": request}
            ).data,
            "sent_invitations": TeamInvitationSerializer(
                sent_invitations, many=True
            ).data,
            "received_invitations": TeamInvitationSerializer(
                received_invitations, many=True
            ).data,
            "latest_transactions": TransactionSerializer(
                latest_transactions, many=True
            ).data,
        }
        return Response(data)


class TopPlayersView(APIView):
    """
    API view for getting top players by prize money.
    """

    def get(self, request):
        users = User.objects.annotate(
            total_winnings=models.Sum(
                "wallet__transaction__amount",
                filter=models.Q(wallet__transaction__transaction_type="prize"),
            )
        ).order_by("-total_winnings")
        serializer = TopPlayerSerializer(users, many=True)
        return Response(serializer.data)


class TopTeamsView(APIView):
    """
    API view for getting top teams by prize money.
    """

    def get(self, request):
        teams = Team.objects.annotate(
            total_winnings=models.Sum(
                "members__wallet__transaction__amount",
                filter=models.Q(members__wallet__transaction__transaction_type="prize"),
            )
        ).order_by("-total_winnings")
        serializer = TopTeamSerializer(teams, many=True)
        return Response(serializer.data)


class TotalPlayersView(APIView):
    """
    API view for getting the total number of players.
    """

    def get(self, request):
        total_players = User.objects.count()
        return Response({"total_players": total_players})

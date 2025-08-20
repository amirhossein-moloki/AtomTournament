from django.db import models
from django.db.models import Count, F, Prefetch, Q, Sum
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tournaments.models import Participant, Tournament
from tournaments.serializers import TournamentReadOnlySerializer
from wallet.models import Transaction
from wallet.serializers import TransactionSerializer

from .models import Role, Team, TeamInvitation, User
from .permissions import (IsAdminUser, IsCaptain, IsCaptainOrReadOnly,
                          IsOwnerOrReadOnly)
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (AdminLoginSerializer, RoleSerializer,
                          TeamInvitationSerializer, TeamSerializer,
                          TopPlayerByRankSerializer, TopPlayerSerializer,
                          TopTeamSerializer, UserCreateSerializer,
                          UserReadOnlySerializer, UserSerializer)
from .services import (ApplicationError, invite_member_service,
                       leave_team_service, remove_member_service,
                       respond_to_invitation_service, send_otp_service,
                       verify_otp_service)


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

    queryset = (
        User.objects.all()
        .prefetch_related("in_game_ids")
        .select_related("verification", "rank")
    )
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["username", "email"]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("list", "retrieve"):
            # Use read-only serializer for lists or for retrieving other users
            if self.action == "retrieve" and self.request.user.is_authenticated and self.get_object() == self.request.user:
                return UserSerializer  # The user is viewing their own profile
            return UserReadOnlySerializer
        return UserSerializer  # For update, partial_update, etc.

    def get_permissions(self):
        if self.action in ["create", "send_otp", "verify_otp"]:
            return [AllowAny()]
        return super().get_permissions()

    @action(detail=True, methods=["get"])
    def tournaments(self, request, pk=None):
        user = self.get_object()
        participant_queryset = Participant.objects.select_related("user")
        tournaments = Tournament.objects.filter(participants=user).prefetch_related(
            Prefetch("participant_set", queryset=participant_queryset), "teams", "game"
        )
        serializer = TournamentReadOnlySerializer(
            tournaments, many=True, context={"request": request}
        )
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

    queryset = Team.objects.all().select_related("captain").prefetch_related("members")
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
            "upcoming_tournaments": TournamentReadOnlySerializer(
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


class TopPlayersByRankView(APIView):
    """
    API view for getting top players by rank.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        users = (
            User.objects.annotate(
                total_winnings=Sum(
                    "wallet__transaction__amount",
                    filter=Q(wallet__transaction__transaction_type="prize"),
                    default=0,
                ),
                wins=Count("won_matches", distinct=True),
            )
            .order_by(F("rank__required_score").desc(nulls_last=True), "-score")
        )
        serializer = TopPlayerByRankSerializer(users, many=True)
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


from django.db.models import Q
from rest_framework import generics
from tournaments.models import Match
from tournaments.serializers import MatchReadOnlySerializer


class TotalPlayersView(APIView):
    """
    API view for getting the total number of players.
    """

    def get(self, request):
        total_players = User.objects.count()
        return Response({"total_players": total_players})


class UserMatchHistoryView(generics.ListAPIView):
    """
    API view to list match history for a specific user.
    """

    serializer_class = MatchReadOnlySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_id = self.kwargs["pk"]
        return Match.objects.filter(
            Q(participant1_user__id=user_id)
            | Q(participant2_user__id=user_id)
            | Q(participant1_team__members__id=user_id)
            | Q(participant2_team__members__id=user_id)
        ).distinct()


class TeamMatchHistoryView(generics.ListAPIView):
    """
    API view to list match history for a specific team.
    """

    serializer_class = MatchReadOnlySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        team_id = self.kwargs["pk"]
        return Match.objects.filter(
            Q(participant1_team__id=team_id) | Q(participant2_team__id=team_id)
        ).distinct()


class AdminLoginView(APIView):
    """
    API view for admin login.
    """

    permission_classes = [AllowAny]
    serializer_class = AdminLoginSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_staff:
                refresh = RefreshToken.for_user(user)
                return Response(
                    {
                        "refresh": str(refresh),
                        "access": str(refresh.access_token),
                    }
                )
            else:
                return Response(
                    {"error": "You are not authorized to login from here."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        else:
            return Response(
                {"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED
            )

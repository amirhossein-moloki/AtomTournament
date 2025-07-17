import random
import string

from django.db import models
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from notifications.tasks import (
    send_email_notification,
    send_sms_notification,
)
from .models import OTP, Role, Team, User, TeamInvitation
from .permissions import (IsAdminUser, IsCaptain, IsCaptainOrReadOnly,
                          IsOwnerOrReadOnly)
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

    @action(detail=False, methods=["post"])
    def send_otp(self, request):
        """
        Send OTP to user.
        """
        phone_number = request.data.get("phone_number")
        email = request.data.get("email")
        if not phone_number and not email:
            return Response(
                {"error": "Phone number or email is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = None
        if phone_number:
            try:
                user = User.objects.get(phone_number=phone_number)
            except User.DoesNotExist:
                pass
        if email and not user:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response(
                    {"error": "User not found."}, status=status.HTTP_400_BAD_REQUEST
                )
        if not user:
            return Response(
                {"error": "User not found."}, status=status.HTTP_400_BAD_REQUEST
            )

        otp = OTP.objects.create(
            user=user, code="".join(random.choices(string.digits, k=6))
        )
        # Send SMS
        if user.phone_number:
            send_sms_notification.delay(
                str(user.phone_number), {"code": otp.code}
            )
        # Send Email
        if user.email:
            send_email_notification.delay(
                user.email, "OTP Code", {"code": otp.code}
            )
        return Response(
            {"message": "OTP sent successfully."}, status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["post"])
    def verify_otp(self, request):
        """
        Verify OTP and login user.
        """
        phone_number = request.data.get("phone_number")
        email = request.data.get("email")
        code = request.data.get("code")
        if not code or (not phone_number and not email):
            return Response(
                {"error": "Phone number or email and code are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = None
        if phone_number:
            try:
                user = User.objects.get(phone_number=phone_number)
            except User.DoesNotExist:
                pass
        if email and not user:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response(
                    {"error": "User not found."}, status=status.HTTP_400_BAD_REQUEST
                )
        if not user:
            return Response(
                {"error": "User not found."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            otp = OTP.objects.get(user=user, code=code, is_active=True)
            if (
                timezone.now() - otp.created_at
            ).total_seconds() > 300:  # 5 minutes
                otp.is_active = False
                otp.save()
                return Response(
                    {"error": "OTP expired."}, status=status.HTTP_400_BAD_REQUEST
                )
            otp.is_active = False
            otp.save()
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                }
            )
        except OTP.DoesNotExist:
            return Response(
                {"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST
            )




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

    @action(detail=True, methods=["post"], permission_classes=[IsCaptain])
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
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found."}, status=status.HTTP_400_BAD_REQUEST
            )
        if user in team.members.all():
            return Response(
                {"error": "User is already a member of the team."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        invitation, created = TeamInvitation.objects.get_or_create(
            from_user=request.user, to_user=user, team=team
        )
        if not created:
            return Response(
                {"error": "Invitation already sent."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"message": "Invitation sent successfully."}, status=status.HTTP_200_OK
        )

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
        status = request.data.get("status")
        if not invitation_id or not status:
            return Response(
                {"error": "Invitation ID and status are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            invitation = TeamInvitation.objects.get(
                id=invitation_id, to_user=request.user
            )
        except TeamInvitation.DoesNotExist:
            return Response(
                {"error": "Invitation not found."}, status=status.HTTP_400_BAD_REQUEST
            )
        if status == "accepted":
            invitation.status = "accepted"
            invitation.team.members.add(request.user)
            invitation.save()
            return Response(
                {"message": "Invitation accepted."}, status=status.HTTP_200_OK
            )
        elif status == "rejected":
            invitation.status = "rejected"
            invitation.save()
            return Response(
                {"message": "Invitation rejected."}, status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"error": "Invalid status."}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def leave_team(self, request, pk=None):
        """
        Leave a team.
        """
        team = self.get_object()
        if request.user not in team.members.all():
            return Response(
                {"error": "You are not a member of this team."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if request.user == team.captain:
            return Response(
                {"error": "The captain cannot leave the team."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        team.members.remove(request.user)
        return Response(
            {"message": "You have left the team."}, status=status.HTTP_200_OK
        )

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
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found."}, status=status.HTTP_400_BAD_REQUEST
            )
        if user not in team.members.all():
            return Response(
                {"error": "User is not a member of the team."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if user == team.captain:
            return Response(
                {"error": "The captain cannot be removed from the team."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        team.members.remove(user)
        return Response(
            {"message": "Member removed successfully."}, status=status.HTTP_200_OK
        )


class DashboardView(APIView):
    """
    API view for user dashboard.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        upcoming_tournaments = user.tournaments.filter(
            start_date__gte=timezone.now()
        ).order_by("start_date")
        sent_invitations = user.sent_invitations.filter(status="pending")
        received_invitations = user.received_invitations.filter(status="pending")
        latest_transactions = user.wallet.transaction_set.order_by("-timestamp")[:5]

        data = {
            "upcoming_tournaments": TournamentSerializer(
                upcoming_tournaments, many=True
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
            total_winnings=models.Sum("wallet__transaction__amount", filter=models.Q(wallet__transaction__transaction_type="prize"))
        ).order_by("-total_winnings")
        serializer = TopPlayerSerializer(users, many=True)
        return Response(serializer.data)


class TopTeamsView(APIView):
    """
    API view for getting top teams by prize money.
    """

    def get(self, request):
        teams = Team.objects.annotate(
            total_winnings=models.Sum("members__wallet__transaction__amount", filter=models.Q(members__wallet__transaction__transaction_type="prize"))
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

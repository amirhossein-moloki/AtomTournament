from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Count, F, Prefetch, Q, Sum
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django_filters.rest_framework import DjangoFilterBackend
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from tournaments.models import Participant, Tournament
from tournaments.serializers import (TournamentListSerializer,
                                     TournamentReadOnlySerializer)
from wallet.models import Transaction
from wallet.serializers import TransactionSerializer
from teams.models import Team
from .models import Role, User
from .permissions import (IsAdminUser, IsOwnerOrReadOnly)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from .serializers import CustomTokenObtainPairSerializer

from .serializers import (RoleSerializer,
                          TopPlayerByRankSerializer, TopPlayerSerializer,
                          UserCreateSerializer,
                          UserReadOnlySerializer, UserSerializer)
from .services import (ApplicationError, send_otp_service,
                       verify_otp_service)
from common.throttles import (
    VeryStrictThrottle,
    StrictThrottle,
    MediumThrottle,
    RelaxedThrottle,
)


class CustomTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [VeryStrictThrottle]
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        user = serializer.user
        if not settings.DEBUG and not user.is_staff:
            return Response(
                {"error": "You are not authorized to login from here."},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(serializer.validated_data, status=status.HTTP_200_OK)


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
    permission_classes = [IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["username", "email"]

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            # Use read-only serializer for lists or for retrieving other users
            if self.action == "retrieve" and self.request.user.is_authenticated and self.get_object() == self.request.user:
                return UserSerializer  # The user is viewing their own profile
            return UserReadOnlySerializer
        return UserSerializer  # For update, partial_update, etc.

    def get_permissions(self):
        if self.action in ["send_otp", "verify_otp"]:
            return [AllowAny()]
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticatedOrReadOnly()]
        return super().get_permissions()

    @action(detail=True, methods=["get"])
    def tournaments(self, request, pk=None):
        user = self.get_object()
        participant_queryset = Participant.objects.select_related("user")
        tournaments = Tournament.objects.filter(participants=user).prefetch_related(
            Prefetch("participant_set", queryset=participant_queryset), "teams", "game"
        )
        serializer = TournamentListSerializer(
            tournaments, many=True, context={"request": request}
        )
        return Response(serializer.data)

    def get_throttles(self):
        if self.action in ['send_otp', 'verify_otp']:
            self.throttle_classes = [VeryStrictThrottle]
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.throttle_classes = [StrictThrottle]
        elif self.action in ['list', 'retrieve']:
            self.throttle_classes = [MediumThrottle]
        else:
            self.throttle_classes = [RelaxedThrottle]
        return super().get_throttles()

    @action(detail=False, methods=["post"])
    def send_otp(self, request):
        """
        Send OTP to user based on email or phone number.
        """
        identifier = request.data.get("identifier")
        try:
            send_otp_service(identifier=identifier)
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
        identifier = request.data.get("identifier")
        code = request.data.get("code")
        try:
            user = verify_otp_service(identifier=identifier, code=code)
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                }
            )
        except ApplicationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],
        url_path="me",
    )
    def me(self, request):
        """
        Return the authenticated user's data.
        """
        user = self.get_queryset().get(pk=request.user.pk)
        serializer = UserSerializer(user, context={"request": request})
        return Response(serializer.data)


class DashboardView(APIView):
    """
    API view for user dashboard.
    Provides all necessary data for the main dashboard UI.
    """
    permission_classes = [IsAuthenticated]

    @method_decorator(cache_page(60 * 5))
    @method_decorator(vary_on_headers("Authorization"))
    def get(self, request):
        user = request.user

        # Serialize user profile data
        user_profile_data = UserSerializer(user, context={'request': request}).data

        # Get user's teams
        teams = Team.objects.filter(members=user).prefetch_related('members')
        teams_data = []
        for team in teams:
            teams_data.append({
                'id': team.id,
                'name': team.name,
                'team_picture': request.build_absolute_uri(team.team_picture.url) if team.team_picture else None,
                'members_count': team.members.count(),
                'is_captain': team.captain == user,
            })

        # Get user's tournament history (Optimized with Prefetch)
        user_teams = user.teams.all()
        user_participations = Participant.objects.filter(user=user).select_related(
            'tournament', 'tournament__game'
        ).prefetch_related(
            Prefetch('tournament__teams', queryset=user_teams, to_attr='user_teams_in_tournament')
        ).order_by('-tournament__start_date')

        tournament_history_data = []
        for p in user_participations:
            team_name = None
            if p.tournament.type == 'team' and hasattr(p.tournament, 'user_teams_in_tournament'):
                user_team = next((team for team in p.tournament.user_teams_in_tournament), None)
                if user_team:
                    team_name = user_team.name

            tournament_history_data.append({
                'id': p.id,
                'rank': p.rank,
                'prize': p.prize,
                'team': {'name': team_name} if team_name else None,
                'tournament': {
                    'name': p.tournament.name,
                    'game': {'name': p.tournament.game.name},
                    'start_date': p.tournament.start_date,
                }
            })

        data = {
            'user_profile': user_profile_data,
            'teams': teams_data,
            'tournament_history': tournament_history_data,
        }
        return Response(data)


class TopPlayersView(APIView):
    """
    API view for getting top players by prize money.
    """
    permission_classes = [AllowAny]

    @method_decorator(cache_page(60 * 15))
    def get(self, request):
        users = User.objects.annotate(
            total_winnings=models.Sum(
                "wallet__transactions__amount",
                filter=models.Q(wallet__transactions__transaction_type="prize"),
            )
        ).order_by("-total_winnings")
        serializer = TopPlayerSerializer(users, many=True)
        return Response(serializer.data)


class TopPlayersByRankView(APIView):
    """
    API view for getting top players by rank.
    """

    permission_classes = [AllowAny]

    @method_decorator(cache_page(60 * 15))
    def get(self, request):
        users = (
            User.objects.annotate(
                total_winnings=Sum(
                    "wallet__transactions__amount",
                    filter=Q(wallet__transactions__transaction_type="prize"),
                    default=0,
                ),
                wins=Count("won_matches", distinct=True),
            )
            .order_by(F("rank__required_score").desc(nulls_last=True), "-score")
        )
        serializer = TopPlayerByRankSerializer(users, many=True)
        return Response(serializer.data)


from django.db.models import Q
from rest_framework import generics
from tournaments.models import Match
from tournaments.serializers import MatchReadOnlySerializer


class TotalPlayersView(APIView):
    """
    API view for getting the total number of players.
    """
    permission_classes = [AllowAny]

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


class GoogleLoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [VeryStrictThrottle]

    def post(self, request):
        try:
            token = request.data.get("id_token")
            if not token:
                return Response(
                    {"error": "ID token is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Verify the token
            id_info = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID
            )

            email = id_info.get("email")
            if not email:
                return Response(
                    {"error": "Email not found in token."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if user exists
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response(
                    {"error": "User with this email does not exist."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Generate tokens for the user
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                }
            )

        except ValueError as e:
            # Invalid token
            return Response(
                {"error": f"Invalid token: {e}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # In a real-world scenario, you would log the error `e` here
            return Response(
                {"error": "An unexpected error occurred. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

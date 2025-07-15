from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Role, Team, User
from .permissions import (IsAdminUser, IsCaptain, IsCaptainOrReadOnly,
                          IsOwnerOrReadOnly)
from .serializers import RoleSerializer, TeamSerializer, UserSerializer


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
        if self.action == "create":
            return [AllowAny()]
        return super().get_permissions()




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
    def add_member(self, request, pk=None):
        """
        Add a member to a team.
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
        team.members.add(user)
        return Response(TeamSerializer(team).data, status=status.HTTP_200_OK)

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
        team.members.remove(user)
        return Response(TeamSerializer(team).data, status=status.HTTP_200_OK)

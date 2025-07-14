from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from users.permissions import IsAdminUser
from wallet.services import distribute_prize, pay_entry_fee

from .models import Game, Match, Tournament
from .permissions import IsTournamentParticipant
from .serializers import GameSerializer, MatchSerializer, TournamentSerializer
from .services import generate_matches, record_match_result


class GameViewSet(viewsets.ModelViewSet):
    queryset = Game.objects.all()
    serializer_class = GameSerializer
    permission_classes = [IsAdminUser]


class TournamentViewSet(viewsets.ModelViewSet):
    queryset = Tournament.objects.all()
    serializer_class = TournamentSerializer
    permission_classes = [IsAuthenticated, IsTournamentParticipant]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["name", "game", "type", "is_free"]

    from django.db import transaction

    from .services import (generate_matches,
                           join_tournament)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsTournamentParticipant],
    )
    def join(self, request, pk=None):
        tournament = self.get_object()
        user = request.user

        try:
            with transaction.atomic():
                pay_entry_fee(user, tournament)
                join_tournament(tournament, user)
            return Response(TournamentSerializer(tournament).data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminUser])
    def generate_matches(self, request, pk=None):
        tournament = self.get_object()
        try:
            generate_matches(tournament)
            return Response({"detail": "Matches generated successfully."})
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminUser])
    def distribute_prizes(self, request, pk=None):
        tournament = self.get_object()
        try:
            distribute_prize(tournament)
            return Response({"detail": "Prizes distributed successfully."})
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


from .permissions import IsMatchParticipant, IsTournamentParticipant


class MatchViewSet(viewsets.ModelViewSet):
    queryset = Match.objects.all()
    serializer_class = MatchSerializer
    permission_classes = [IsAuthenticated, IsMatchParticipant]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["tournament", "round", "is_confirmed", "is_disputed"]

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsMatchParticipant],
    )
    def confirm_result(self, request, pk=None):
        match = self.get_object()
        winner_id = request.data.get("winner_id")
        proof_image = request.data.get("proof_image")

        if not winner_id:
            return Response(
                {"detail": "Winner ID is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            record_match_result(match, winner_id, proof_image)
            return Response(MatchSerializer(match).data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

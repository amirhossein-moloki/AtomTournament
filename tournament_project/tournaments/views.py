from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from .models import Game, Tournament, Match
from .serializers import GameSerializer, TournamentSerializer, MatchSerializer
from .services import generate_matches, confirm_match_result
from users.permissions import IsAdminUser
from wallet.services import pay_entry_fee, distribute_prize

class GameViewSet(viewsets.ModelViewSet):
    queryset = Game.objects.all()
    serializer_class = GameSerializer
    permission_classes = [IsAdminUser]

class TournamentViewSet(viewsets.ModelViewSet):
    queryset = Tournament.objects.all()
    serializer_class = TournamentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['name', 'game', 'type', 'is_free']

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def join(self, request, pk=None):
        tournament = self.get_object()
        user = request.user

        if tournament.type == 'individual':
            if user in tournament.participants.all():
                return Response({'detail': 'You have already joined this tournament.'}, status=status.HTTP_400_BAD_REQUEST)

            pay_entry_fee(user, tournament)
            tournament.participants.add(user)
            return Response(TournamentSerializer(tournament).data)

        elif tournament.type == 'team':
            team = user.teams.first() # Assuming a user can only be in one team for simplicity
            if not team:
                return Response({'detail': 'You are not a member of any team.'}, status=status.HTTP_400_BAD_REQUEST)
            if team in tournament.teams.all():
                return Response({'detail': 'Your team has already joined this tournament.'}, status=status.HTTP_400_BAD_REQUEST)

            pay_entry_fee(user, tournament) # Assuming the captain pays the fee
            tournament.teams.add(team)
            return Response(TournamentSerializer(tournament).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def generate_matches(self, request, pk=None):
        tournament = self.get_object()
        try:
            generate_matches(tournament)
            return Response({'detail': 'Matches generated successfully.'})
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def distribute_prizes(self, request, pk=None):
        tournament = self.get_object()
        try:
            distribute_prize(tournament)
            return Response({'detail': 'Prizes distributed successfully.'})
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class MatchViewSet(viewsets.ModelViewSet):
    queryset = Match.objects.all()
    serializer_class = MatchSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['tournament', 'round', 'is_confirmed', 'is_disputed']

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def confirm_result(self, request, pk=None):
        match = self.get_object()
        winner_id = request.data.get('winner_id')
        proof_image = request.data.get('proof_image')

        if not winner_id:
            return Response({'detail': 'Winner ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if match.match_type == 'individual':
                winner = match.tournament.participants.get(id=winner_id)
            else:
                winner = match.tournament.teams.get(id=winner_id)

            confirm_match_result(match, winner, proof_image)
            return Response(MatchSerializer(match).data)
        except (Tournament.participants.model.DoesNotExist, Tournament.teams.model.DoesNotExist):
            return Response({'detail': 'Invalid winner ID.'}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

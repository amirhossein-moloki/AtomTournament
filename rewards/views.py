import random
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Wheel, Prize, Spin
from .serializers import WheelSerializer, PrizeSerializer, SpinSerializer


class WheelViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Wheel.objects.all()
    serializer_class = WheelSerializer

    @action(detail=True, methods=["post"])
    def spin(self, request, pk=None):
        wheel = self.get_object()
        user = request.user
        if user.rank.id < wheel.required_rank.id:
            return Response(
                {"error": "You do not have the required rank to spin this wheel."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if Spin.objects.filter(user=user, wheel=wheel).exists():
            return Response(
                {"error": "You have already spun this wheel."},
                status=status.HTTP_403_FORBIDDEN,
            )
        prizes = wheel.prizes.all()
        prize = random.choices(prizes, weights=[p.chance for p in prizes])[0]
        spin = Spin.objects.create(user=user, wheel=wheel, prize=prize)
        serializer = SpinSerializer(spin)
        return Response(serializer.data)

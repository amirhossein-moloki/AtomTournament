import random

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from users.models import User

from .models import Spin, Wheel
from .serializers import SpinSerializer, WheelSerializer


class WheelViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Wheel.objects.all().prefetch_related("prizes", "required_rank")
    serializer_class = WheelSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def spin(self, request, pk=None):
        wheel = self.get_object()
        user = User.objects.select_related("rank").get(pk=request.user.pk)

        if Spin.objects.filter(user=user, wheel=wheel).exists():
            return Response(
                {"error": "You have already spun this wheel."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if (
            user.rank is None
            or user.rank.required_score < wheel.required_rank.required_score
        ):
            return Response(
                {"error": "You do not have the required rank to spin this wheel."},
                status=status.HTTP_403_FORBIDDEN,
            )
        prizes = wheel.prizes.all()
        if not prizes:
            return Response(
                {"error": "This wheel has no prizes."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        prize = random.choices(prizes, weights=[p.chance for p in prizes])[0]
        spin = Spin.objects.create(user=user, wheel=wheel, prize=prize)
        serializer = SpinSerializer(spin)
        return Response(serializer.data)


class SpinViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Spin.objects.all()
    serializer_class = SpinSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Spin.objects.filter(user=self.request.user).select_related(
            "wheel", "prize"
        )

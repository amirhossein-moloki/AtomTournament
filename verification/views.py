from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from .models import Verification
from .serializers import VerificationSerializer

class VerificationViewSet(viewsets.GenericViewSet):
    serializer_class = VerificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Verification.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def status(self, request):
        instance, created = Verification.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def submit_level2(self, request):
        verification, created = Verification.objects.get_or_create(user=request.user)
        if verification.level >= 2 and verification.is_verified:
            return Response({"detail": "You are already verified at level 2 or higher."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        id_card_image = serializer.validated_data.get("id_card_image")
        selfie_image = serializer.validated_data.get("selfie_image")

        if not id_card_image or not selfie_image:
            return Response({"detail": "Both ID card image and selfie image are required."}, status=status.HTTP_400_BAD_REQUEST)

        verification.id_card_image = id_card_image
        verification.selfie_image = selfie_image
        verification.level = 2
        verification.is_verified = False
        verification.save()

        return Response({"detail": "Your verification request has been submitted."}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def submit_level3(self, request):
        verification, created = Verification.objects.get_or_create(user=request.user)
        if verification.level >= 3 and verification.is_verified:
            return Response({"detail": "You are already verified at level 3."}, status=status.HTTP_400_BAD_REQUEST)

        if verification.level < 2 or not verification.is_verified:
            return Response({"detail": "You must be verified at level 2 before you can apply for level 3."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        video = serializer.validated_data.get("video")

        if not video:
            return Response({"detail": "Video is required."}, status=status.HTTP_400_BAD_REQUEST)

        verification.video = video
        verification.level = 3
        verification.is_verified = False
        verification.save()

        return Response({"detail": "Your verification request has been submitted."}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def approve(self, request, pk=None):
        try:
            instance = Verification.objects.get(pk=pk)
        except Verification.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        is_verified = request.data.get("is_verified")

        if is_verified is None:
            return Response({"detail": "is_verified field is required."}, status=status.HTTP_400_BAD_REQUEST)

        instance.is_verified = is_verified
        instance.save()

        return Response({"detail": "Verification status updated successfully."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def list_all(self, request):
        queryset = Verification.objects.all().select_related('user')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

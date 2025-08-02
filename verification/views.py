from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework import status
from .models import Verification
from .serializers import VerificationSerializer


class VerificationLevel2View(generics.CreateAPIView):
    serializer_class = VerificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        user = request.user
        verification, created = Verification.objects.get_or_create(user=user)
        if verification.level >= 2 and verification.is_verified:
            return Response(
                {"detail": "You are already verified at level 2 or higher."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        id_card_image = serializer.validated_data.get("id_card_image")
        selfie_image = serializer.validated_data.get("selfie_image")

        if not id_card_image or not selfie_image:
            return Response(
                {"detail": "Both ID card image and selfie image are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        verification.id_card_image = id_card_image
        verification.selfie_image = selfie_image
        verification.level = 2
        verification.is_verified = False
        verification.save()

        return Response(
            {"detail": "Your verification request has been submitted."},
            status=status.HTTP_201_CREATED,
        )


class AdminVerificationView(generics.UpdateAPIView):
    serializer_class = VerificationSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = Verification.objects.all()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        is_verified = request.data.get("is_verified")

        if is_verified is None:
            return Response(
                {"detail": "is_verified field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance.is_verified = is_verified
        instance.save()

        return Response(
            {"detail": "Verification status updated successfully."},
            status=status.HTTP_200_OK,
        )


class VerificationLevel3View(generics.CreateAPIView):
    serializer_class = VerificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        user = request.user
        verification, created = Verification.objects.get_or_create(user=user)
        if verification.level >= 3 and verification.is_verified:
            return Response(
                {"detail": "You are already verified at level 3."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if verification.level < 2 or not verification.is_verified:
            return Response(
                {
                    "detail": "You must be verified at level 2 before you can apply for level 3."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        video = serializer.validated_data.get("video")

        if not video:
            return Response(
                {"detail": "Video is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        verification.video = video
        verification.level = 3
        verification.is_verified = False
        verification.save()

        return Response(
            {"detail": "Your verification request has been submitted."},
            status=status.HTTP_201_CREATED,
        )

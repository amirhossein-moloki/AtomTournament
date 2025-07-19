from rest_framework import generics, permissions
from .authentication_models import Level2AuthenticationRequest, Level3AuthenticationRequest
from .authentication_serializers import Level2AuthenticationRequestSerializer, Level3AuthenticationRequestSerializer


from rest_framework.response import Response


class Level2AuthenticationRequestView(generics.CreateAPIView):
    queryset = Level2AuthenticationRequest.objects.all()
    serializer_class = Level2AuthenticationRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class Level3AuthenticationRequestView(generics.CreateAPIView):
    queryset = Level3AuthenticationRequest.objects.all()
    serializer_class = Level3AuthenticationRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class GetLevel3TextToReadView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        obj, created = Level3AuthenticationRequest.objects.get_or_create(user=self.request.user)
        return Response({"text_to_read": obj.text_to_read})

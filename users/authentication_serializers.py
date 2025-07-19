from rest_framework import serializers
from .authentication_models import Level2AuthenticationRequest, Level3AuthenticationRequest


class Level2AuthenticationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Level2AuthenticationRequest
        fields = ("selfie", "id_card")


class Level3AuthenticationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Level3AuthenticationRequest
        fields = ("video",)

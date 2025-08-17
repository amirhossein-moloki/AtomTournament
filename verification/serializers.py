from rest_framework import serializers

from .models import Verification


class VerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Verification
        fields = (
            "id",
            "user",
            "level",
            "id_card_image",
            "selfie_image",
            "video",
            "is_verified",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class VerificationLevel2Serializer(serializers.ModelSerializer):
    id_card_image = serializers.ImageField(required=True)
    selfie_image = serializers.ImageField(required=True)

    class Meta:
        model = Verification
        fields = ("id_card_image", "selfie_image")


class VerificationLevel3Serializer(serializers.ModelSerializer):
    video = serializers.FileField(required=True)

    class Meta:
        model = Verification
        fields = ("video",)

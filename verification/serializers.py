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
        read_only_fields = (
            "id",
            "user",
            "level",
            "is_verified",
            "created_at",
            "updated_at",
        )

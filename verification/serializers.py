from rest_framework import serializers
from .models import Verification

class VerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Verification
        fields = ['id_card_image', 'selfie_image', 'video']

from rest_framework import serializers
from .models import BotSettings

class BotSettingsSerializer(serializers.ModelSerializer):
    """
    Serializer for the BotSettings model.
    The 'is_active' field is the only writable field.
    """
    class Meta:
        model = BotSettings
        fields = ['id', 'name', 'is_active', 'author']
        read_only_fields = ['id', 'name', 'author']

from rest_framework import serializers

from .models import Prize, Spin, Wheel


class PrizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prize
        fields = ("id", "wheel", "name", "image", "chance")
        read_only_fields = fields


class WheelSerializer(serializers.ModelSerializer):
    prizes = PrizeSerializer(many=True, read_only=True)

    class Meta:
        model = Wheel
        fields = ("id", "name", "required_rank", "prizes")
        read_only_fields = fields


class SpinSerializer(serializers.ModelSerializer):
    class Meta:
        model = Spin
        fields = ("id", "user", "wheel", "prize", "timestamp")
        read_only_fields = fields

from rest_framework import serializers

from .models import Prize, Spin, Wheel


class PrizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prize
        fields = "__all__"


class WheelSerializer(serializers.ModelSerializer):
    prizes = PrizeSerializer(many=True, read_only=True)

    class Meta:
        model = Wheel
        fields = "__all__"


class SpinSerializer(serializers.ModelSerializer):
    class Meta:
        model = Spin
        fields = "__all__"

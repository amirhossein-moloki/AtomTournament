from django.utils.translation import gettext, override
from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    notification_type_display = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = (
            "id",
            "user",
            "message",
            "notification_type",
            "notification_type_display",
            "is_read",
            "timestamp",
        )
        read_only_fields = (
            "id",
            "user",
            "message",
            "notification_type",
            "notification_type_display",
            "timestamp",
        )

    def to_representation(self, instance):
        with override("fa"):
            data = super().to_representation(instance)
            data["message"] = gettext(instance.message)
        return data

    def get_notification_type_display(self, obj):
        with override("fa"):
            return obj.get_notification_type_display()

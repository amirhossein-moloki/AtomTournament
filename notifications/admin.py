from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "message", "notification_type", "is_read", "timestamp")
    list_filter = ("notification_type", "is_read", "timestamp")
    search_fields = ("user__username", "message")
    readonly_fields = ("user", "message", "notification_type", "timestamp")

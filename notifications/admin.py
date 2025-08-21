# Django Imports
from django.contrib import admin
from django.db import models

# 3rd-party Imports
from unfold.admin import ModelAdmin
from simple_history.admin import SimpleHistoryAdmin
from import_export.admin import ImportExportModelAdmin
from import_export import resources
from django_select2.forms import Select2Widget

# Local Imports
from .models import Notification


# --- Resources for django-import-export ---

class NotificationResource(resources.ModelResource):
    class Meta:
        model = Notification


# --- ModelAdmins (Upgraded) ---

@admin.register(Notification)
class NotificationAdmin(ImportExportModelAdmin, SimpleHistoryAdmin, ModelAdmin):
    resource_class = NotificationResource
    list_display = ("user", "message", "notification_type", "is_read", "timestamp")
    list_filter = ("notification_type", "is_read", "timestamp")
    search_fields = ("user__username", "message")
    autocomplete_fields = ("user",)
    readonly_fields = ("user", "message", "notification_type", "timestamp")

    formfield_overrides = {
        models.ForeignKey: {"widget": Select2Widget},
    }

    fieldsets = (
        (None, {"fields": ("user", "notification_type", "is_read")}),
        ("Content", {"fields": ("message", "timestamp")}),
    )

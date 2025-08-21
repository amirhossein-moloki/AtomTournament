# Django Imports
from django.contrib import admin, messages
from django.db import models

# 3rd-party Imports
from unfold.admin import ModelAdmin
from simple_history.admin import SimpleHistoryAdmin
from import_export.admin import ImportExportModelAdmin
from import_export import resources
from django_select2.forms import Select2Widget

# Local Imports
from .models import Verification


# --- Resources for django-import-export ---

class VerificationResource(resources.ModelResource):
    class Meta:
        model = Verification


# --- ModelAdmins (Upgraded) ---

@admin.register(Verification)
class VerificationAdmin(ImportExportModelAdmin, SimpleHistoryAdmin, ModelAdmin):
    resource_class = VerificationResource
    list_display = ("user", "level", "is_verified", "updated_at")
    list_filter = ("level", "is_verified")
    search_fields = ("user__username",)
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")
    actions = ["approve_verifications", "reject_verifications"]

    formfield_overrides = {
        models.ForeignKey: {"widget": Select2Widget},
    }

    fieldsets = (
        ("User Info", {"fields": ("user",), "classes": ("tab",)}),
        ("Verification Details", {"fields": ("level", "is_verified", "id_card_image", "selfie_image", "video"), "classes": ("tab",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("tab",)}),
    )

    def approve_verifications(self, request, queryset):
        updated_count = queryset.update(is_verified=True)
        self.message_user(request, f"{updated_count} verifications approved.", "success")
    approve_verifications.short_description = "Approve selected verifications"

    def reject_verifications(self, request, queryset):
        updated_count = queryset.update(is_verified=False)
        self.message_user(request, f"{updated_count} verifications rejected.", "warning")
    reject_verifications.short_description = "Reject selected verifications"

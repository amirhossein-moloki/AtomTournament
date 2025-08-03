from django.contrib import admin

from .models import Verification


@admin.register(Verification)
class VerificationAdmin(admin.ModelAdmin):
    list_display = ("user", "level", "is_verified", "created_at", "updated_at")
    list_filter = ("level", "is_verified", "created_at")
    search_fields = ("user__username",)
    readonly_fields = ("user", "created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("user", "level", "is_verified")}),
        (
            "Verification Documents",
            {"fields": ("id_card_image", "selfie_image", "video")},
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

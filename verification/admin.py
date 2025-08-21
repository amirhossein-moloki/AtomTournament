from django.contrib import admin, messages

from .models import Verification


@admin.register(Verification)
class VerificationAdmin(admin.ModelAdmin):
    list_display = ("user", "level", "is_verified", "updated_at")
    list_filter = ("level", "is_verified")
    search_fields = ("user__username",)
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")
    actions = ["approve_verifications", "reject_verifications"]

    fieldsets = (
        ("User Info", {"fields": ("user",)}),
        (
            "Verification Details",
            {
                "fields": (
                    "level",
                    "is_verified",
                    "id_card_image",
                    "selfie_image",
                    "video",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    def approve_verifications(self, request, queryset):
        updated_count = queryset.update(is_verified=True)
        self.message_user(
            request,
            f"{updated_count} verifications have been approved.",
            messages.SUCCESS,
        )

    approve_verifications.short_description = "Approve selected verifications"

    def reject_verifications(self, request, queryset):
        updated_count = queryset.update(is_verified=False)
        self.message_user(
            request,
            f"{updated_count} verifications have been rejected.",
            messages.WARNING,
        )

    reject_verifications.short_description = "Reject selected verifications"

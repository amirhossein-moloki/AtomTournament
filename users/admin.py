from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    InGameID,
    OTP,
    Role,
    Team,
    TeamInvitation,
    TeamMembership,
    User,
)


class InGameIDInline(admin.TabularInline):
    model = InGameID
    extra = 1
    autocomplete_fields = ("game",)


class TeamMembershipInline(admin.TabularInline):
    model = TeamMembership
    extra = 1
    autocomplete_fields = ("team",)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "email",
        "phone_number",
        "score",
        "rank",
        "is_staff",
    )
    search_fields = ("username", "first_name", "last_name", "email", "phone_number")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups", "rank")
    autocomplete_fields = ("rank", "groups")
    inlines = [InGameIDInline, TeamMembershipInline]
    readonly_fields = ("score", "rank")

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "Personal info",
            {"fields": ("first_name", "last_name", "email", "phone_number")},
        ),
        ("Game Profile", {"fields": ("score", "rank", "profile_picture")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    actions = ["reset_score"]

    def reset_score(self, request, queryset):
        updated_count = queryset.update(score=0)
        self.message_user(
            request,
            f"{updated_count} users had their score reset to 0.",
            messages.SUCCESS,
        )

    reset_score.short_description = "Reset score of selected users"


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("group", "is_default")
    search_fields = ("group__name",)
    list_filter = ("is_default",)
    autocomplete_fields = ("group",)


@admin.register(InGameID)
class InGameIDAdmin(admin.ModelAdmin):
    list_display = ("user", "game", "player_id")
    search_fields = ("user__username", "game__name", "player_id")
    autocomplete_fields = ("user", "game")


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "captain", "max_members")
    search_fields = ("name", "captain__username")
    autocomplete_fields = ("captain", "members")
    inlines = [TeamMembershipInline]

    fieldsets = (
        ("Team Info", {"fields": ("name", "team_picture", "captain", "max_members")}),
        ("Members", {"fields": ("members",)}),
    )


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "team", "date_joined")
    search_fields = ("user__username", "team__name")
    autocomplete_fields = ("user", "team")


@admin.register(TeamInvitation)
class TeamInvitationAdmin(admin.ModelAdmin):
    list_display = ("from_user", "to_user", "team", "status", "timestamp")
    search_fields = ("from_user__username", "to_user__username", "team__name")
    list_filter = ("status",)
    autocomplete_fields = ("from_user", "to_user", "team")


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ("user", "code", "created_at", "is_active")
    search_fields = ("user__username",)
    list_filter = ("is_active",)
    autocomplete_fields = ("user",)

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from .models import (OTP, InGameID, Role, Team, TeamInvitation, TeamMembership,
                     User)


class InGameIDInline(admin.TabularInline):
    model = InGameID
    extra = 1


class TeamMembershipInline(admin.TabularInline):
    model = TeamMembership
    extra = 1
    readonly_fields = ("user", "team", "date_joined")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            None,
            {
                "fields": (
                    "phone_number",
                    "profile_picture",
                    "profile_picture_preview",
                    "score",
                    "rank",
                )
            },
        ),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (None, {"fields": ("phone_number", "profile_picture", "score", "rank")}),
    )
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
        "get_score",
        "rank",
        "team_count",
        "profile_picture_preview",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "groups", "rank")
    search_fields = ("username", "first_name", "last_name", "email", "phone_number")
    inlines = [InGameIDInline, TeamMembershipInline]
    readonly_fields = ("profile_picture_preview",)
    actions = ["make_active", "make_inactive"]

    def get_score(self, obj):
        return obj.score

    get_score.short_description = "امتیاز"  # This is 'Score' in Persian

    def profile_picture_preview(self, obj):
        if obj.profile_picture:
            return format_html(
                '<img src="{}" width="50" height="50" />', obj.profile_picture.url
            )
        return "No Image"

    profile_picture_preview.short_description = "Profile Picture Preview"

    def team_count(self, obj):
        return obj.teams.count()

    team_count.short_description = "Teams"

    def make_active(self, request, queryset):
        queryset.update(is_active=True)

    make_active.short_description = "Mark selected users as active"

    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)

    make_inactive.short_description = "Mark selected users as inactive"


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("group", "description", "is_default")
    list_filter = ("is_default",)
    search_fields = ("group__name", "description")


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "captain", "member_count")
    search_fields = ("name", "captain__username")
    inlines = [TeamMembershipInline]

    def member_count(self, obj):
        return obj.members.count()

    member_count.short_description = "Members"


@admin.register(TeamInvitation)
class TeamInvitationAdmin(admin.ModelAdmin):
    list_display = ("from_user", "to_user", "team", "status", "timestamp")
    list_filter = ("status", "timestamp")
    search_fields = ("from_user__username", "to_user__username", "team__name")


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ("user", "code", "created_at", "is_active")
    list_filter = ("is_active", "created_at")
    search_fields = ("user__username",)
    readonly_fields = ("user", "code", "created_at")


# TeamMembership is managed through inlines, but it's good to register it too.
@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "team", "date_joined")
    search_fields = ("user__username", "team__name")
    readonly_fields = ("user", "team", "date_joined")


# InGameID is managed through inlines, but it's good to register it too.
@admin.register(InGameID)
class InGameIDAdmin(admin.ModelAdmin):
    list_display = ("user", "game", "player_id")
    search_fields = ("user__username", "game__name", "player_id")

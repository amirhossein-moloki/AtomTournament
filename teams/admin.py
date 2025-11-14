from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin, TabularInline

from .models import Team, TeamInvitation, TeamMembership


class TeamMembershipInline(TabularInline):
    model = TeamMembership
    extra = 1
    autocomplete_fields = ("user", "team")
    classes = ["collapse"]


@admin.register(Team)
class TeamAdmin(SimpleHistoryAdmin, ModelAdmin):
    list_display = ("name", "captain", "max_members")
    search_fields = ("name", "captain__username")
    autocomplete_fields = ("captain",)
    inlines = [TeamMembershipInline]

    fieldsets = (
        ("Team Info", {"fields": ("name", "team_picture", "captain", "max_members")}),
    )


@admin.register(TeamMembership)
class TeamMembershipAdmin(ModelAdmin):
    list_display = ("user", "team", "date_joined")
    search_fields = ("user__username", "team__name")
    autocomplete_fields = ("user", "team")


@admin.register(TeamInvitation)
class TeamInvitationAdmin(ModelAdmin):
    list_display = ("from_user", "to_user", "team", "status", "timestamp")
    search_fields = ("from_user__username", "to_user__username", "team__name")
    list_filter = ("status",)
    autocomplete_fields = ("from_user", "to_user", "team")

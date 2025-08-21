# Django Imports
from django.contrib import admin
from django.db import models

# 3rd-party Imports
from unfold.admin import ModelAdmin, TabularInline
# from unfold.decorators import register  <- This was incorrect and is removed.
from import_export.admin import ImportExportModelAdmin
from import_export import resources
from simple_history.admin import SimpleHistoryAdmin
from guardian.admin import GuardedModelAdmin
from django_select2.forms import Select2Widget
from tempus_dominus.widgets import DateTimePicker

# Local Imports
from .models import (
    Game,
    GameImage,
    GameManager,
    Match,
    Participant,
    Rank,
    Report,
    Scoring,
    Tournament,
    WinnerSubmission,
)
from .mixins import AdminAlertsMixin


# --- Resources for django-import-export ---

class TournamentResource(resources.ModelResource):
    class Meta:
        model = Tournament
        fields = ('id', 'name', 'game__name', 'type', 'mode', 'start_date', 'end_date', 'is_free', 'entry_fee')
        export_order = fields


# --- Inlines (using Unfold's TabularInline) ---

class GameManagerInline(TabularInline):
    model = GameManager
    extra = 1
    autocomplete_fields = ("user",)
    classes = ["collapse"]


class GameImageInline(TabularInline):
    model = GameImage
    extra = 1
    classes = ["collapse"]


class ParticipantInline(TabularInline):
    model = Participant
    extra = 0
    autocomplete_fields = ("user",)
    classes = ["collapse"]


class MatchInline(TabularInline):
    model = Match
    extra = 0
    autocomplete_fields = (
        "participant1_user", "participant2_user",
        "participant1_team", "participant2_team",
        "winner_user", "winner_team",
    )
    show_change_link = True
    classes = ["collapse"]


class ScoringInline(TabularInline):
    model = Scoring
    extra = 0
    autocomplete_fields = ("user",)
    classes = ["collapse"]


class ReportInline(TabularInline):
    model = Report
    extra = 0
    autocomplete_fields = ("reporter", "reported_user")
    show_change_link = True


# --- ModelAdmins (Corrected to use @admin.register) ---

@admin.register(Rank)
class RankAdmin(ModelAdmin):
    list_display = ("name", "required_score")
    search_fields = ("name",)


@admin.register(Game)
class GameAdmin(ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    inlines = [GameManagerInline, GameImageInline]


@admin.register(GameManager)
class GameManagerAdmin(ModelAdmin):
    list_display = ("user", "game")
    autocomplete_fields = ("user", "game")
    search_fields = ("user__username", "game__name")


@admin.register(Scoring)
class ScoringAdmin(ModelAdmin):
    list_display = ("tournament", "user", "score")
    autocomplete_fields = ("tournament", "user")
    search_fields = ("tournament__name", "user__username")


@admin.register(GameImage)
class GameImageAdmin(ModelAdmin):
    list_display = ("game", "image_type")
    list_filter = ("image_type",)
    autocomplete_fields = ("game",)


@admin.register(Tournament)
class TournamentAdmin(
    AdminAlertsMixin,
    ImportExportModelAdmin,
    SimpleHistoryAdmin,
    GuardedModelAdmin,
    ModelAdmin,
):
    resource_class = TournamentResource
    list_display = ("name", "game", "type", "mode", "start_date", "is_free")
    list_display_links = ("name",)
    list_filter = ("type", "mode", "is_free", "game")
    search_fields = ("name", "game__name")
    history_list_display = ["history_type", "history_user", "history_date"]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related("game", "creator").prefetch_related(
            "participants", "teams"
        )

    formfield_overrides = {
        models.ForeignKey: {"widget": Select2Widget},
        models.DateTimeField: {
            "widget": DateTimePicker(
                options={"useCurrent": True, "collapse": False},
                attrs={"append": "fa fa-calendar", "icon_toggle": True},
            )
        },
    }

    fieldsets = (
        ("Tournament Info", {"fields": ("name", "game", "creator", "rules"), "classes": ("tab",)}),
        ("Configuration", {"fields": ("type", "mode", "max_participants", "team_size", "is_free", "entry_fee"), "classes": ("tab",)}),
        ("Schedule", {"fields": ("start_date", "end_date", "countdown_start_time"), "classes": ("tab",)}),
        ("Restrictions & Participants", {"fields": ("required_verification_level", "min_rank", "max_rank", "top_players", "top_teams"), "classes": ("tab",)}),
    )
    inlines = [ParticipantInline, MatchInline, ScoringInline]


@admin.register(Participant)
class ParticipantAdmin(SimpleHistoryAdmin, ModelAdmin):
    list_display = ("user", "tournament", "status", "rank", "prize")
    list_filter = ("status", "tournament")
    search_fields = ("user__username", "tournament__name")
    autocomplete_fields = ("user", "tournament")
    history_list_display = ["status"]


@admin.register(Match)
class MatchAdmin(SimpleHistoryAdmin, ModelAdmin):
    list_display = ("tournament", "round", "__str__", "is_confirmed", "is_disputed")
    list_filter = ("is_confirmed", "is_disputed", "tournament", "match_type")
    search_fields = ("tournament__name", "participant1_user__username", "participant2_user__username")
    autocomplete_fields = ("tournament", "participant1_user", "participant2_user", "participant1_team", "participant2_team", "winner_user", "winner_team")
    inlines = [ReportInline]
    history_list_display = ["history_type", "history_user", "history_date"]
    actions = ["confirm_matches"]

    fieldsets = (
        ("Match Info", {"fields": ("tournament", "round", "match_type"), "classes": ("tab",)}),
        ("Participants", {"fields": ("participant1_user", "participant2_user", "participant1_team", "participant2_team"), "classes": ("tab",)}),
        ("Result & Status", {"fields": ("winner_user", "winner_team", "result_proof", "is_confirmed", "is_disputed", "dispute_reason"), "classes": ("tab",)}),
        ("Connection", {"fields": ("room_id", "password"), "classes": ("tab",)}),
    )

    def confirm_matches(self, request, queryset):
        updated_count = queryset.update(is_confirmed=True)
        self.message_user(request, f"{updated_count} matches confirmed.", "success")
    confirm_matches.short_description = "Confirm selected matches"


@admin.register(Report)
class ReportAdmin(ModelAdmin):
    list_display = ("reporter", "reported_user", "match", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("reporter__username", "reported_user__username", "match__tournament__name")
    autocomplete_fields = ("reporter", "reported_user", "match")
    actions = ["resolve_reports", "reject_reports"]

    def resolve_reports(self, request, queryset):
        updated_count = queryset.update(status="resolved")
        self.message_user(request, f"{updated_count} reports resolved.", "success")
    resolve_reports.short_description = "Mark selected reports as resolved"

    def reject_reports(self, request, queryset):
        updated_count = queryset.update(status="rejected")
        self.message_user(request, f"{updated_count} reports rejected.", "success")
    reject_reports.short_description = "Mark selected reports as rejected"


@admin.register(WinnerSubmission)
class WinnerSubmissionAdmin(ModelAdmin):
    list_display = ("winner", "tournament", "status", "created_at")
    list_filter = ("status", "tournament")
    search_fields = ("winner__username", "tournament__name")
    autocomplete_fields = ("winner", "tournament")

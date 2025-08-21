from django.contrib import admin, messages

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


class GameManagerInline(admin.TabularInline):
    model = GameManager
    extra = 1
    autocomplete_fields = ("user",)


class GameImageInline(admin.TabularInline):
    model = GameImage
    extra = 1


class ParticipantInline(admin.TabularInline):
    model = Participant
    extra = 1
    autocomplete_fields = ("user",)


class MatchInline(admin.TabularInline):
    model = Match
    extra = 1
    autocomplete_fields = (
        "participant1_user",
        "participant2_user",
        "participant1_team",
        "participant2_team",
        "winner_user",
        "winner_team",
    )
    show_change_link = True


class ScoringInline(admin.TabularInline):
    model = Scoring
    extra = 1
    autocomplete_fields = ("user",)


class ReportInline(admin.TabularInline):
    model = Report
    extra = 1
    autocomplete_fields = ("reporter", "reported_user")
    show_change_link = True


@admin.register(Rank)
class RankAdmin(admin.ModelAdmin):
    list_display = ("name", "required_score")
    search_fields = ("name",)


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    inlines = [GameManagerInline, GameImageInline]


@admin.register(GameManager)
class GameManagerAdmin(admin.ModelAdmin):
    list_display = ("user", "game")
    autocomplete_fields = ("user", "game")


@admin.register(Scoring)
class ScoringAdmin(admin.ModelAdmin):
    list_display = ("tournament", "user", "score")
    autocomplete_fields = ("tournament", "user")


@admin.register(GameImage)
class GameImageAdmin(admin.ModelAdmin):
    list_display = ("game", "image_type")
    list_filter = ("image_type",)
    autocomplete_fields = ("game",)


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ("name", "game", "type", "mode", "start_date", "end_date", "is_free")
    search_fields = ("name", "game__name")
    list_filter = ("type", "mode", "is_free", "game", "start_date", "end_date")
    autocomplete_fields = (
        "game",
        "participants",
        "teams",
        "creator",
        "min_rank",
        "max_rank",
        "top_players",
        "top_teams",
    )
    inlines = [ParticipantInline, MatchInline, ScoringInline]
    fieldsets = (
        ("Tournament Info", {"fields": ("name", "game", "creator", "rules")}),
        (
            "Configuration",
            {
                "fields": (
                    "type",
                    "mode",
                    "max_participants",
                    "team_size",
                    "is_free",
                    "entry_fee",
                )
            },
        ),
        ("Schedule", {"fields": ("start_date", "end_date", "countdown_start_time")}),
        (
            "Restrictions",
            {"fields": ("required_verification_level", "min_rank", "max_rank")},
        ),
        (
            "Participants & Winners",
            {"fields": ("participants", "teams", "top_players", "top_teams")},
        ),
    )


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ("user", "tournament", "status", "rank", "prize")
    list_filter = ("status", "tournament")
    search_fields = ("user__username", "tournament__name")
    autocomplete_fields = ("user", "tournament")


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = (
        "tournament",
        "round",
        "__str__",
        "is_confirmed",
        "is_disputed",
    )
    list_filter = ("is_confirmed", "is_disputed", "tournament", "match_type")
    search_fields = (
        "tournament__name",
        "participant1_user__username",
        "participant2_user__username",
        "participant1_team__name",
        "participant2_team__name",
    )
    autocomplete_fields = (
        "tournament",
        "participant1_user",
        "participant2_user",
        "participant1_team",
        "participant2_team",
        "winner_user",
        "winner_team",
    )
    inlines = [ReportInline]
    actions = ["confirm_matches"]

    fieldsets = (
        ("Match Info", {"fields": ("tournament", "round", "match_type")}),
        (
            "Participants",
            {
                "fields": (
                    "participant1_user",
                    "participant2_user",
                    "participant1_team",
                    "participant2_team",
                )
            },
        ),
        ("Result", {"fields": ("winner_user", "winner_team", "result_proof")}),
        (
            "Status",
            {"fields": ("is_confirmed", "is_disputed", "dispute_reason")},
        ),
        ("Connection Details", {"fields": ("room_id", "password")}),
    )

    def confirm_matches(self, request, queryset):
        updated_count = queryset.update(is_confirmed=True)
        self.message_user(
            request, f"{updated_count} matches have been confirmed.", messages.SUCCESS
        )

    confirm_matches.short_description = "Confirm selected matches"


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("reporter", "reported_user", "match", "status", "created_at")
    list_filter = ("status",)
    search_fields = (
        "reporter__username",
        "reported_user__username",
        "match__tournament__name",
    )
    autocomplete_fields = ("reporter", "reported_user", "match")
    actions = ["resolve_reports", "reject_reports"]

    def resolve_reports(self, request, queryset):
        updated_count = queryset.update(status="resolved")
        self.message_user(
            request, f"{updated_count} reports have been resolved.", messages.SUCCESS
        )

    resolve_reports.short_description = "Mark selected reports as resolved"

    def reject_reports(self, request, queryset):
        updated_count = queryset.update(status="rejected")
        self.message_user(
            request, f"{updated_count} reports have been rejected.", messages.SUCCESS
        )

    reject_reports.short_description = "Mark selected reports as rejected"


@admin.register(WinnerSubmission)
class WinnerSubmissionAdmin(admin.ModelAdmin):
    list_display = ("winner", "tournament", "status", "created_at")
    list_filter = ("status", "tournament")
    search_fields = ("winner__username", "tournament__name")
    autocomplete_fields = ("winner", "tournament")

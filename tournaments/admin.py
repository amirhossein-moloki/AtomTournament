from django.contrib import admin

from .models import (Game, GameImage, GameManager, Match, Participant, Rank,
                     Report, Scoring, Tournament, WinnerSubmission)


@admin.register(Rank)
class RankAdmin(admin.ModelAdmin):
    list_display = ("name", "required_score", "image")
    search_fields = ("name",)


class GameImageInline(admin.TabularInline):
    model = GameImage
    extra = 1


class GameManagerInline(admin.TabularInline):
    model = GameManager
    extra = 1


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    inlines = [GameImageInline, GameManagerInline]


class ParticipantInline(admin.TabularInline):
    model = Participant
    extra = 1
    readonly_fields = ("user", "status", "rank", "prize")


class MatchInline(admin.TabularInline):
    model = Match
    extra = 1


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ("name", "game", "type", "start_date", "end_date", "is_free")
    list_filter = ("game", "type", "is_free", "start_date")
    search_fields = ("name", "game__name")
    inlines = [ParticipantInline, MatchInline]


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ("user", "tournament", "status", "rank", "prize")
    list_filter = ("tournament", "status")
    search_fields = ("user__username", "tournament__name")
    readonly_fields = ("user", "tournament", "rank", "prize")


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = (
        "tournament",
        "round",
        "match_type",
        "participant1_user",
        "participant2_user",
        "winner_user",
    )
    list_filter = ("tournament", "match_type", "round")
    search_fields = (
        "tournament__name",
        "participant1_user__username",
        "participant2_user__username",
    )


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("reporter", "reported_user", "match", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("reporter__username", "reported_user__username", "match__id")


@admin.register(WinnerSubmission)
class WinnerSubmissionAdmin(admin.ModelAdmin):
    list_display = ("winner", "tournament", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("winner__username", "tournament__name")


@admin.register(Scoring)
class ScoringAdmin(admin.ModelAdmin):
    list_display = ("tournament", "user", "score")
    search_fields = ("tournament__name", "user__username")


# GameImage and GameManager are managed through inlines, but it's good to register them too.
@admin.register(GameImage)
class GameImageAdmin(admin.ModelAdmin):
    list_display = ("game", "image_type", "image")
    list_filter = ("image_type",)
    search_fields = ("game__name",)


@admin.register(GameManager)
class GameManagerAdmin(admin.ModelAdmin):
    list_display = ("user", "game")
    search_fields = ("user__username", "game__name")

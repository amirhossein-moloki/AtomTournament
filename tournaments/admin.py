from django.contrib import admin
from .models import (
    Game,
    GameImage,
    Tournament,
    TournamentManager,
    Match,
    Participant,
    Report,
    WinnerSubmission,
)


class GameImageInline(admin.TabularInline):
    model = GameImage
    extra = 1


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    inlines = [GameImageInline]


class TournamentManagerInline(admin.TabularInline):
    model = TournamentManager
    extra = 1


class TournamentAdmin(admin.ModelAdmin):
    list_display = ('name', 'game', 'start_date', 'end_date', 'type', 'is_free')
    list_filter = ('type', 'is_free', 'game')
    search_fields = ('name', 'game__name')
    inlines = [TournamentManagerInline]


# Unregister the basic Tournament admin and re-register with the custom one
if admin.site.is_registered(Tournament):
    admin.site.unregister(Tournament)
admin.site.register(Tournament, TournamentAdmin)

admin.site.register(Match)
admin.site.register(Participant)
admin.site.register(Report)
admin.site.register(WinnerSubmission)

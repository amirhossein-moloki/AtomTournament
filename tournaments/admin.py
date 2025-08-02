from django.contrib import admin
from .models import (
    Game,
    GameImage,
    Tournament,
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


admin.site.register(Tournament)
admin.site.register(Match)
admin.site.register(Participant)
admin.site.register(Report)
admin.site.register(WinnerSubmission)

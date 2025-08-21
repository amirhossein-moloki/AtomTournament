from django.contrib import admin

from .models import Prize, Spin, Wheel


class PrizeInline(admin.TabularInline):
    model = Prize
    extra = 1


@admin.register(Wheel)
class WheelAdmin(admin.ModelAdmin):
    list_display = ("name", "required_rank")
    search_fields = ("name",)
    autocomplete_fields = ("required_rank",)
    inlines = [PrizeInline]


@admin.register(Prize)
class PrizeAdmin(admin.ModelAdmin):
    list_display = ("name", "wheel", "chance")
    search_fields = ("name",)
    autocomplete_fields = ("wheel",)


@admin.register(Spin)
class SpinAdmin(admin.ModelAdmin):
    list_display = ("user", "wheel", "prize", "timestamp")
    search_fields = ("user__username", "wheel__name", "prize__name")
    autocomplete_fields = ("user", "wheel", "prize")

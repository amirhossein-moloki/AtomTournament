from django.contrib import admin

from .models import Prize, Spin, Wheel


class PrizeInline(admin.TabularInline):
    model = Prize
    extra = 1


@admin.register(Wheel)
class WheelAdmin(admin.ModelAdmin):
    list_display = ("name", "required_rank")
    list_filter = ("required_rank",)
    search_fields = ("name",)
    inlines = [PrizeInline]


@admin.register(Prize)
class PrizeAdmin(admin.ModelAdmin):
    list_display = ("name", "wheel", "chance")
    list_filter = ("wheel",)
    search_fields = ("name", "wheel__name")


@admin.register(Spin)
class SpinAdmin(admin.ModelAdmin):
    list_display = ("user", "wheel", "prize", "timestamp")
    list_filter = ("wheel", "timestamp")
    search_fields = ("user__username", "wheel__name", "prize__name")
    readonly_fields = ("user", "wheel", "prize", "timestamp")

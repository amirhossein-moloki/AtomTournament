from django.contrib import admin

from .models import SupportAssignment, Ticket, TicketMessage


class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 1
    readonly_fields = ("user", "message", "created_at")


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("title", "user__username")
    inlines = [TicketMessageInline]
    readonly_fields = ("user", "created_at")


@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display = ("ticket", "user", "created_at")
    list_filter = ("created_at",)
    search_fields = ("ticket__title", "user__username")
    readonly_fields = ("ticket", "user", "message", "created_at")


@admin.register(SupportAssignment)
class SupportAssignmentAdmin(admin.ModelAdmin):
    list_display = ("support_person", "game", "head_support")
    list_filter = ("game", "head_support")
    search_fields = ("support_person__username", "game__name")

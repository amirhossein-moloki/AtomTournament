from django.contrib import admin, messages

from chat.models import Conversation
from .models import SupportAssignment, Ticket, TicketMessage


class ConversationInline(admin.TabularInline):
    model = Conversation
    extra = 0
    verbose_name_plural = "Conversations"
    can_delete = False
    show_change_link = True
    fields = ("id", "created_at")
    readonly_fields = ("id", "created_at")

    def has_add_permission(self, request, obj=None):
        return False


class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 1
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at",)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("title", "user__username")
    autocomplete_fields = ("user",)
    inlines = [TicketMessageInline, ConversationInline]
    actions = ["close_tickets"]

    fieldsets = (
        ("Ticket Details", {"fields": ("title", "user", "status")}),
        ("Timestamps", {"fields": ("created_at",)}),
    )
    readonly_fields = ("created_at",)

    def close_tickets(self, request, queryset):
        updated_count = queryset.update(status="closed")
        self.message_user(
            request,
            f"{updated_count} tickets have been marked as closed.",
            messages.SUCCESS,
        )

    close_tickets.short_description = "Close selected tickets"


@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display = ("ticket", "user", "created_at")
    search_fields = ("ticket__title", "user__username", "message")
    autocomplete_fields = ("ticket", "user")
    readonly_fields = ("created_at",)


@admin.register(SupportAssignment)
class SupportAssignmentAdmin(admin.ModelAdmin):
    list_display = ("support_person", "game", "head_support")
    list_filter = ("head_support", "game")
    search_fields = ("support_person__username", "game__name")
    autocomplete_fields = ("support_person", "game")

# Django Imports
from django.contrib import admin, messages
from django.db import models

# 3rd-party Imports
from unfold.admin import ModelAdmin, TabularInline
from simple_history.admin import SimpleHistoryAdmin
from django_select2.forms import Select2Widget

# Local Imports
from chat.models import Conversation
from .models import SupportAssignment, Ticket, TicketMessage


# --- Inlines (Upgraded) ---

class ConversationInline(TabularInline):
    model = Conversation
    extra = 0
    verbose_name_plural = "Conversations"
    can_delete = False
    show_change_link = True
    fields = ("id", "created_at")
    readonly_fields = ("id", "created_at")

    def has_add_permission(self, request, obj=None):
        return False


class TicketMessageInline(TabularInline):
    model = TicketMessage
    extra = 0
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at",)
    classes = ["collapse"]


# --- ModelAdmins (Upgraded) ---

@admin.register(Ticket)
class TicketAdmin(SimpleHistoryAdmin, ModelAdmin):
    list_display = ("title", "user", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("title", "user__username")
    autocomplete_fields = ("user",)
    inlines = [TicketMessageInline, ConversationInline]
    actions = ["close_tickets", "answer_tickets"]
    readonly_fields = ("created_at",)

    formfield_overrides = {
        models.ForeignKey: {"widget": Select2Widget},
    }

    fieldsets = (
        ("Ticket Details", {"fields": ("title", "user", "status"), "classes": ("tab",)}),
        ("Timestamps", {"fields": ("created_at",), "classes": ("tab",)}),
    )

    def close_tickets(self, request, queryset):
        updated_count = queryset.update(status="closed")
        self.message_user(
            request,
            f"{updated_count} tickets have been marked as closed.",
            "success",
        )
    close_tickets.short_description = "Close selected tickets"

    def answer_tickets(self, request, queryset):
        updated_count = queryset.update(status="answered")
        self.message_user(
            request,
            f"{updated_count} tickets have been marked as answered.",
            "success",
        )
    answer_tickets.short_description = "Answer selected tickets"


@admin.register(TicketMessage)
class TicketMessageAdmin(ModelAdmin):
    list_display = ("ticket", "user", "created_at")
    search_fields = ("ticket__title", "user__username", "message")
    autocomplete_fields = ("ticket", "user")
    readonly_fields = ("created_at",)


@admin.register(SupportAssignment)
class SupportAssignmentAdmin(SimpleHistoryAdmin, ModelAdmin):
    list_display = ("support_person", "game", "head_support")
    list_filter = ("head_support", "game")
    search_fields = ("support_person__username", "game__name")
    autocomplete_fields = ("support_person", "game")

# Django Imports
from django.contrib import admin
from django.db import models

# 3rd-party Imports
from unfold.admin import ModelAdmin, TabularInline
from simple_history.admin import SimpleHistoryAdmin
from import_export.admin import ImportExportModelAdmin
from import_export import resources
from django_select2.forms import Select2Widget

# Local Imports
from .models import Attachment, Conversation, Message


# --- Resources for django-import-export ---

class ConversationResource(resources.ModelResource):
    class Meta:
        model = Conversation

class MessageResource(resources.ModelResource):
    class Meta:
        model = Message

class AttachmentResource(resources.ModelResource):
    class Meta:
        model = Attachment


# --- Inlines (Upgraded) ---

class MessageInline(TabularInline):
    model = Message
    extra = 0
    autocomplete_fields = ("sender",)
    classes = ["collapse"]


class AttachmentInline(TabularInline):
    model = Attachment
    extra = 0
    classes = ["collapse"]


# --- ModelAdmins (Upgraded) ---

@admin.register(Conversation)
class ConversationAdmin(ImportExportModelAdmin, SimpleHistoryAdmin, ModelAdmin):
    resource_class = ConversationResource
    list_display = ("id", "created_at", "support_ticket")
    search_fields = ("participants__username", "support_ticket__title")
    autocomplete_fields = ("participants", "support_ticket")
    inlines = [MessageInline]
    formfield_overrides = {
        models.ManyToManyField: {"widget": Select2Widget},
        models.ForeignKey: {"widget": Select2Widget},
    }


@admin.register(Message)
class MessageAdmin(ImportExportModelAdmin, SimpleHistoryAdmin, ModelAdmin):
    resource_class = MessageResource
    list_display = ("sender", "conversation", "timestamp", "is_read")
    list_filter = ("is_read", "timestamp")
    search_fields = ("sender__username", "content")
    autocomplete_fields = ("conversation", "sender")
    inlines = [AttachmentInline]
    readonly_fields = ("timestamp",)
    formfield_overrides = {
        models.ForeignKey: {"widget": Select2Widget},
    }


@admin.register(Attachment)
class AttachmentAdmin(ImportExportModelAdmin, SimpleHistoryAdmin, ModelAdmin):
    resource_class = AttachmentResource
    list_display = ("message", "file", "uploaded_at")
    autocomplete_fields = ("message",)
    readonly_fields = ("uploaded_at",)
    formfield_overrides = {
        models.ForeignKey: {"widget": Select2Widget},
    }

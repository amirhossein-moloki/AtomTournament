from django.contrib import admin

from .models import Attachment, Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 1
    autocomplete_fields = ("sender",)


class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 1


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "support_ticket")
    search_fields = ("participants__username", "support_ticket__title")
    autocomplete_fields = ("participants", "support_ticket")
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("sender", "conversation", "timestamp", "is_read")
    list_filter = ("is_read", "timestamp")
    search_fields = ("sender__username", "content")
    autocomplete_fields = ("conversation", "sender")
    inlines = [AttachmentInline]


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ("message", "file", "uploaded_at")
    autocomplete_fields = ("message",)

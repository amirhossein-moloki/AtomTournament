from django.contrib import admin
from .models import Conversation, Message, Attachment

class MessageInline(admin.TabularInline):
    model = Message
    extra = 1
    readonly_fields = ('sender', 'content', 'timestamp', 'is_read', 'is_edited', 'is_deleted')

class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 1

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'support_ticket')
    list_filter = ('created_at',)
    search_fields = ('participants__username', 'support_ticket__title')
    inlines = [MessageInline]

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender', 'timestamp', 'is_read', 'is_edited', 'is_deleted')
    list_filter = ('timestamp', 'is_read', 'is_edited', 'is_deleted')
    search_fields = ('sender__username', 'content')
    inlines = [AttachmentInline]

@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'message', 'file', 'uploaded_at')
    list_filter = ('uploaded_at',)
    search_fields = ('message__id',)

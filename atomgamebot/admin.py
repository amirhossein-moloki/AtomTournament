from django.contrib import admin
from .models import BotSettings

@admin.register(BotSettings)
class BotSettingsAdmin(admin.ModelAdmin):
    """
    Admin configuration for the BotSettings model.
    This configuration prevents the creation of new BotSettings instances
    and the deletion of existing ones from the admin interface.
    """
    list_display = ('name', 'author', 'is_active')
    list_editable = ('is_active',)
    list_display_links = ('name',)

    def has_add_permission(self, request):
        # Prevent creating new settings instances if one already exists.
        return not BotSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Prevent deleting the settings from the admin.
        return False

from rest_framework import generics, permissions
from .models import BotSettings
from .serializers import BotSettingsSerializer

class BotSettingsAPIView(generics.RetrieveUpdateAPIView):
    """
    API view to retrieve and update the AtomGameBot settings.
    Allows GET to view the current settings and PUT/PATCH to update them.
    Only admin users have permission to modify the settings.
    """
    serializer_class = BotSettingsSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_object(self):
        """
        This view should always operate on the single, specific BotSettings
        instance for AtomGameBot. We use get_or_create to ensure it always
        exists.
        """
        obj, created = BotSettings.objects.get_or_create(name="AtomGameBot")
        return obj

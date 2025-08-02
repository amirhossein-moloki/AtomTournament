from rest_framework import permissions

from .models import TournamentManager


class IsTournamentManagerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow admins or tournament managers to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # The user must be authenticated to have any object-level permissions.
        if not request.user or not request.user.is_authenticated:
            return False

        # Admins (staff) have universal access.
        if request.user.is_staff:
            return True

        # Check if the user is a manager for the given tournament ('obj').
        return TournamentManager.objects.filter(user=request.user, tournament=obj).exists()

from rest_framework import permissions

from .models import GameManager


class IsGameManagerOrAdmin(permissions.BasePermission):
    """
    Custom permission to allow access to admins or managers of a specific game.
    - For object-level permissions (update, delete), it checks if the user
      manages the game associated with the tournament.
    - For view-level permissions (create), it checks if the user manages
      the game specified in the request data.
    """

    def has_permission(self, request, view):
        # The user must be authenticated for any action.
        if not request.user or not request.user.is_authenticated:
            return False

        # Allow list/retrieve actions for any authenticated user.
        if view.action in ["list", "retrieve"]:
            return True

        # Admins can do anything.
        if request.user.is_staff:
            return True

        # For 'create' action, we need to check the game from the request data.
        if view.action == "create":
            game_id = request.data.get("game")
            if not game_id:
                return False  # Cannot create a tournament without a game.
            return GameManager.objects.filter(
                user=request.user, game_id=game_id
            ).exists()

        # For other actions (like update, destroy), object-level permission is the source of truth.
        return True

    def has_object_permission(self, request, view, obj):
        # Admins can do anything.
        if request.user.is_staff:
            return True

        # 'obj' is the tournament instance. Check if the user manages its game.
        return GameManager.objects.filter(user=request.user, game=obj.game).exists()

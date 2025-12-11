from rest_framework import permissions

class IsAdminUser(permissions.BasePermission):
    """
    Custom permission to only allow admin users to access a view.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if hasattr(obj, "user"):
            return obj.user == request.user
        if hasattr(obj, "author"):
            return obj.author.user == request.user
        if hasattr(obj, "uploaded_by"):
            return obj.uploaded_by == request.user
        # For User model itself
        if hasattr(obj, "id"):
            return obj.id == request.user.id
        return False

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to allow owners of an object or admins to edit it.
    Handles various ownership attributes.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        if request.user and request.user.is_staff:
            return True

        # Direct user ownership
        if hasattr(obj, "user") and obj.user == request.user:
            return True

        # Ownership via author profile
        if hasattr(obj, "author") and hasattr(obj.author, "user") and obj.author.user == request.user:
            return True

        # Ownership for uploaded files
        if hasattr(obj, "uploaded_by") and obj.uploaded_by == request.user:
            return True

        # Ownership for the User model itself
        if hasattr(obj, "id") and type(obj).__name__ == 'User' and obj.id == request.user.id:
            return True

        # Nested ownership for Support Tickets (TicketMessage -> ticket -> user)
        if hasattr(obj, "ticket") and hasattr(obj.ticket, "user") and obj.ticket.user == request.user:
            return True

        # Ownership for Tournament Reports (Report -> reporter)
        if hasattr(obj, "reporter") and obj.reporter == request.user:
             return True

        # Ownership for Winner Submissions (WinnerSubmission -> winner)
        if hasattr(obj, "winner") and obj.winner == request.user:
            return True

        return False

class IsSelfOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow a user to access their own resource, or for an admin to access any.
    Assumes the object being checked is the user object itself.
    """
    def has_object_permission(self, request, view, obj):
        return bool(request.user and (request.user.is_staff or obj == request.user))

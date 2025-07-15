from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsSenderOrReadOnly(BasePermission):
    """
    Object-level permission to only allow senders of a message to edit or delete it.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        return obj.sender == request.user

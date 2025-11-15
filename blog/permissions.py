from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the snippet.
        # Assumes the model instance has an `author` attribute.
        # For models like Comment or Reaction, it would be `user`.
        if hasattr(obj, 'author'):
            return obj.author.user == request.user
        if hasattr(obj, 'user'):
            return obj.user == request.user
        # For AuthorProfile, the owner is the user itself.
        if hasattr(obj, 'user_id'):
            return obj.user_id == request.user.id

        return False


class IsAdminUserOrReadOnly(permissions.BasePermission):
    """
    Allows read-only access for non-admin users, and full access for admin users.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff

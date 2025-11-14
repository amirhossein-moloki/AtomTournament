from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsTeamMember(BasePermission):
    """
    Custom permission to only allow members of a team to access it.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return request.user in obj.members.all()


class IsCaptain(BasePermission):
    """
    Custom permission to only allow the captain of a team to edit it.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.captain == request.user


class IsCaptainOrReadOnly(BasePermission):
    """
    Custom permission to only allow captains of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.captain == request.user

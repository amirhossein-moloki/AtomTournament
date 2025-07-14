from rest_framework import permissions

class IsTournamentParticipant(permissions.BasePermission):
    """
    Custom permission to only allow participants of a tournament to access it.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        if obj.type == 'individual':
            return obj.participants.filter(id=request.user.id).exists()
        elif obj.type == 'team':
            return obj.teams.filter(members=request.user).exists()
        return False

class IsMatchParticipant(permissions.BasePermission):
    """
    Custom permission to only allow participants of a match to access it.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        if obj.match_type == 'individual':
            return obj.participant1_user == request.user or obj.participant2_user == request.user
        elif obj.match_type == 'team':
            return request.user in obj.participant1_team.members.all() or request.user in obj.participant2_team.members.all()
        return False

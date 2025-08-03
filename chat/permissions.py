from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import Conversation


class IsSenderOrReadOnly(BasePermission):
    """
    Object-level permission to only allow senders of a message to edit or delete it.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        return obj.sender == request.user


class IsParticipantInConversation(BasePermission):
    """
    Custom permission to only allow participants of a conversation to view attachments.
    """

    def has_permission(self, request, view):
        conversation_pk = view.kwargs.get("conversation_pk")
        if not conversation_pk:
            return False  # Should not happen with nested routers
        try:
            conversation = Conversation.objects.get(pk=conversation_pk)
            return request.user in conversation.participants.all()
        except Conversation.DoesNotExist:
            return False

    def has_object_permission(self, request, view, obj):
        return request.user in obj.message.conversation.participants.all()

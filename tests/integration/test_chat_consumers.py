"""
Tests for the chat WebSocket consumer in chat/consumers.py.
These tests cover connection, authentication, message handling, and disconnection.
"""
import pytest
import json
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from channels.routing import URLRouter
from django.urls import path
from chat.consumers import ChatConsumer
from chat.models import Conversation

# Define the ASGI application for testing
application = URLRouter([
    path("ws/chat/<int:conversation_id>/", ChatConsumer.as_asgi()),
])


@pytest.fixture
def conversation(db, default_user):
    """Creates a conversation with the default user as a participant."""
    conv = Conversation.objects.create()
    conv.participants.add(default_user)
    return conv


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestChatConsumer:
    async def test_connect_authenticated(self, default_user, conversation):
        """
        GIVEN an authenticated user
        WHEN they try to connect to a valid conversation WebSocket
        THEN the connection should be accepted.
        """
        communicator = WebsocketCommunicator(
            application, f"/ws/chat/{conversation.id}/"
        )
        communicator.scope["user"] = default_user
        connected, _ = await communicator.connect()
        assert connected
        await communicator.disconnect()

    async def test_connect_unauthenticated(self, conversation):
        """
        GIVEN an unauthenticated user (or AnonymousUser)
        WHEN they try to connect to a WebSocket
        THEN the connection should be rejected/closed.
        """
        from django.contrib.auth.models import AnonymousUser

        communicator = WebsocketCommunicator(
            application, f"/ws/chat/{conversation.id}/"
        )
        communicator.scope["user"] = AnonymousUser()
        connected, close_code = await communicator.connect()
        assert not connected

    async def test_receive_chat_message(self, default_user, conversation):
        """
        GIVEN a connected user
        WHEN they send a chat message
        THEN the message should be saved to the database and broadcast to the group.
        """
        communicator = WebsocketCommunicator(
            application, f"/ws/chat/{conversation.id}/"
        )
        communicator.scope["user"] = default_user
        await communicator.connect()

        await communicator.send_to(
            text_data=json.dumps({"type": "chat_message", "message": "Hello world!"})
        )

        response = await communicator.receive_from()
        data = json.loads(response)

        assert data["sender"] == default_user.username
        assert data["content"] == "Hello world!"
        assert "id" in data

        @database_sync_to_async
        def message_exists():
            return conversation.messages.filter(content="Hello world!").exists()
        assert await message_exists()

        await communicator.disconnect()

    async def test_edit_message(self, default_user, conversation):
        """
        GIVEN a message sent by a user
        WHEN that user sends an edit_message event
        THEN the message content should be updated in the database and broadcast.
        """
        communicator = WebsocketCommunicator(application, f"/ws/chat/{conversation.id}/")
        communicator.scope["user"] = default_user
        await communicator.connect()

        # First, send a message to edit
        @database_sync_to_async
        def create_message():
            return conversation.messages.create(sender=default_user, content="Original message")
        msg = await create_message()

        await communicator.send_to(
            text_data=json.dumps(
                {
                    "type": "edit_message",
                    "message_id": msg.id,
                    "content": "Edited message",
                }
            )
        )

        response = await communicator.receive_from()
        data = json.loads(response)

        assert data["type"] == "message.edited"
        assert data["message"]["id"] == msg.id
        assert data["message"]["content"] == "Edited message"

        @database_sync_to_async
        def refresh_message():
            msg.refresh_from_db()
            return msg

        refreshed_msg = await refresh_message()
        assert refreshed_msg.content == "Edited message"
        assert refreshed_msg.is_edited is True

        await communicator.disconnect()

    async def test_delete_message(self, default_user, conversation):
        """
        GIVEN a message sent by a user
        WHEN that user sends a delete_message event
        THEN the message should be marked as deleted and a confirmation broadcast.
        """
        communicator = WebsocketCommunicator(application, f"/ws/chat/{conversation.id}/")
        communicator.scope["user"] = default_user
        await communicator.connect()

        @database_sync_to_async
        def create_message():
            return conversation.messages.create(sender=default_user, content="A message to delete")
        msg = await create_message()

        await communicator.send_to(
            text_data=json.dumps({"type": "delete_message", "message_id": msg.id})
        )

        response = await communicator.receive_from()
        data = json.loads(response)

        assert data["type"] == "message.deleted"
        assert data["message_id"] == msg.id

        @database_sync_to_async
        def refresh_message():
            msg.refresh_from_db()
            return msg

        refreshed_msg = await refresh_message()
        assert refreshed_msg.is_deleted is True

        await communicator.disconnect()

    async def test_typing_indicator(self, default_user, conversation):
        """
        GIVEN a connected user
        WHEN they send a typing event
        THEN a typing indicator should be broadcast to other users.
        """
        communicator = WebsocketCommunicator(application, f"/ws/chat/{conversation.id}/")
        communicator.scope["user"] = default_user
        await communicator.connect()

        await communicator.send_to(
            text_data=json.dumps({"type": "typing", "is_typing": True})
        )

        response = await communicator.receive_from()
        data = json.loads(response)

        assert data['type'] == 'user.typing'
        assert data['user'] == default_user.username
        assert data['is_typing'] is True

        await communicator.disconnect()

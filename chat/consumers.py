import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import Conversation, Message


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close()
            return

        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.conversation_group_name = f"chat_{self.conversation_id}"

        await self.channel_layer.group_add(
            self.conversation_group_name, self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.conversation_group_name, self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get("type")

        if message_type == "chat_message":
            await self.handle_chat_message(data)
        elif message_type == "edit_message":
            await self.handle_edit_message(data)
        elif message_type == "delete_message":
            await self.handle_delete_message(data)

    async def handle_chat_message(self, data):
        message_content = data["message"]
        conversation = await self.get_conversation()
        message = await self.save_message(conversation, self.user, message_content)

        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                "type": "chat.message",
                "message": {
                    "id": message.id,
                    "sender": self.user.username,
                    "content": message.content,
                    "timestamp": message.timestamp.isoformat(),
                },
            },
        )

    async def handle_edit_message(self, data):
        message_id = data["message_id"]
        new_content = data["content"]
        message = await self.get_message(message_id)

        if message.sender != self.user:
            return  # Or handle error

        message.content = new_content
        message.is_edited = True
        await message.save()

        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                "type": "message.edited",
                "message": {
                    "id": message.id,
                    "content": message.content,
                },
            },
        )

    async def handle_delete_message(self, data):
        message_id = data["message_id"]
        message = await self.get_message(message_id)

        if message.sender != self.user:
            return  # Or handle error

        message.is_deleted = True
        await message.save()

        await self.channel_layer.group_send(
            self.conversation_group_name,
            {"type": "message.deleted", "message_id": message.id},
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["message"]))

    async def message_edited(self, event):
        await self.send(text_data=json.dumps(event))

    async def message_deleted(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def get_conversation(self):
        return Conversation.objects.get(id=self.conversation_id)

    @database_sync_to_async
    def save_message(self, conversation, sender, content):
        return Message.objects.create(
            conversation=conversation, sender=sender, content=content
        )

    @database_sync_to_async
    def get_message(self, message_id):
        return Message.objects.get(id=message_id)

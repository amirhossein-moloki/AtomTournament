from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Conversation, Message

User = get_user_model()


class ChatModelTests(TestCase):
    def test_conversation_and_message_creation(self):
        user1 = User.objects.create_user(
            username="user1", password="p", phone_number="+1"
        )
        user2 = User.objects.create_user(
            username="user2", password="p", phone_number="+2"
        )
        conversation = Conversation.objects.create()
        conversation.participants.add(user1, user2)

        message = Message.objects.create(
            conversation=conversation,
            sender=user1,
            content="Hello, world!",
        )
        self.assertEqual(conversation.participants.count(), 2)
        self.assertEqual(message.content, "Hello, world!")

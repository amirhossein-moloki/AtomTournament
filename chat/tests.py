from django.test import TestCase
from django.contrib.auth import get_user_model
from chat.models import Conversation, Message

User = get_user_model()

class ChatTestCase(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user1", password="password", phone_number="+12125552368"
        )
        self.user2 = User.objects.create_user(
            username="user2", password="password", phone_number="+12125552369"
        )
        self.conversation = Conversation.objects.create()
        self.conversation.participants.add(self.user1, self.user2)

    def test_message_creation(self):
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            content="Hello, world!",
        )
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(message.content, "Hello, world!")
        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.conversation, self.conversation)

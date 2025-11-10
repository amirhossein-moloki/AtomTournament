from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Conversation, Message

User = get_user_model()


class ChatAPITests(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user1", password="p", phone_number="+1"
        )
        self.user2 = User.objects.create_user(
            username="user2", password="p", phone_number="+2"
        )
        self.client.force_authenticate(user=self.user1)

    def test_create_message_and_conversation(self):
        url = reverse("message-list")
        data = {"content": "Hello, world!", "recipient_id": self.user2.id}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(Message.objects.count(), 1)
        conversation = Conversation.objects.first()
        self.assertIn(self.user1, conversation.participants.all())
        self.assertIn(self.user2, conversation.participants.all())
        self.assertEqual(Message.objects.first().conversation, conversation)

from django.db import models
from django.db.models import ImageField
from support.models import Ticket
from users.models import User


class Conversation(models.Model):
    participants = models.ManyToManyField(User, related_name="conversations")
    created_at = models.DateTimeField(auto_now_add=True)
    support_ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="conversations",
        null=True,
        blank=True,
    )

    class Meta:
        app_label = "chat"


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sent_messages"
    )
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        app_label = "chat"

    is_edited = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"Message from {self.sender} in conversation {self.conversation.id}"


class Attachment(models.Model):
    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name="attachments"
    )
    file = ImageField(upload_to="attachments/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attachment for message {self.message.id}"

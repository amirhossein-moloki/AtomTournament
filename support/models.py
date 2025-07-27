from django.db import models
from users.models import User
from tournaments.models import Game


class Ticket(models.Model):
    TICKET_STATUS_CHOICES = (
        ("open", "Open"),
        ("closed", "Closed"),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20, choices=TICKET_STATUS_CHOICES, default="open"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "support"

    def __str__(self):
        return self.title

    class Meta:
        app_label = "support"


class TicketMessage(models.Model):
    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name="messages"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message by {self.user.username} in ticket {self.ticket.title}"

    class Meta:
        app_label = "support"

    class Meta:
        app_label = "support"


class SupportAssignment(models.Model):
    support_person = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    head_support = models.BooleanField(default=False)

    class Meta:
        unique_together = ("support_person", "game")
        app_label = "support"

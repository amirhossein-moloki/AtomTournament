from django.db import models
from users.models import User


class Notification(models.Model):
    NOTIFICATION_TYPE_CHOICES = (
        ("report_new", "New Report"),
        ("report_status_change", "Report Status Change"),
        ("winner_submission_required", "Winner Submission Required"),
        ("winner_submission_status_change", "Winner Submission Status Change"),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    message = models.CharField(max_length=255)
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPE_CHOICES,
        default="report_status_change",
    )
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.message

    class Meta:
        app_label = "notifications"

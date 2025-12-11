from django.db import models

from users.models import User


class Notification(models.Model):
    NOTIFICATION_TYPE_CHOICES = (
        ("report_new", "گزارش جدید"),
        ("report_status_change", "تغییر وضعیت گزارش"),
        ("winner_submission_required", "نیاز به ارسال نتیجه"),
        ("winner_submission_status_change", "تغییر وضعیت ارسال نتیجه"),
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
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

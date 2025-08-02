from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Notification

User = get_user_model()


class NotificationModelTests(TestCase):
    def test_notification_creation(self):
        user = User.objects.create_user(
            username="testuser", password="password", phone_number="+123"
        )
        notification = Notification.objects.create(
            user=user,
            message="Test notification",
            notification_type="report_new",
        )
        self.assertEqual(notification.user, user)
        self.assertEqual(notification.message, "Test notification")
        self.assertEqual(notification.notification_type, "report_new")

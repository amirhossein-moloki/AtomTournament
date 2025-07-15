from django.test import TestCase
from django.core import mail
from .tasks import send_email_notification, send_sms_notification


class NotificationTasksTestCase(TestCase):
    def test_send_email_notification(self):
        send_email_notification.delay(
            "test@example.com",
            "Test Subject",
            {"tournament_name": "Test Tournament"},
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Test Subject")

    def test_send_sms_notification(self):
        # This is a mock test, it does not actually send an SMS
        send_sms_notification.delay(
            "+1234567890", {"tournament_name": "Test Tournament"}
        )
        pass

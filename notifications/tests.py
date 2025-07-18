from django.test import TestCase
from django.core import mail
from .tasks import send_email_notification, send_sms_notification
from unittest.mock import patch


class NotificationTasksTestCase(TestCase):
    @patch('notifications.tasks.send_mail')
    def test_send_email_notification(self, mock_send_mail):
        send_email_notification.delay(
            "test@example.com",
            "Test Subject",
            {"tournament_name": "Test Tournament"},
        )
        self.assertTrue(mock_send_mail.called)

    @patch('notifications.tasks.sms')
    def test_send_sms_notification(self, mock_sms):
        send_sms_notification.delay(
            "+1234567890", {"tournament_name": "Test Tournament"}
        )
        self.assertTrue(mock_sms.send.called)

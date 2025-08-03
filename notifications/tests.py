from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from tournaments.models import Game, Match, Tournament

from .models import Notification
from .tasks import (send_email_notification, send_sms_notification,
                    send_tournament_credentials)

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


class NotificationTaskTests(TestCase):

    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user1",
            password="p",
            phone_number="+111",
            email="user1@test.com",
        )
        self.user2 = User.objects.create_user(
            username="user2",
            password="p",
            phone_number="+222",
            email="user2@test.com",
        )

    @override_settings(SMSIR_API_KEY="dummy_api_key")
    @patch("notifications.tasks.SmsIr")
    def test_send_sms_notification_with_code(self, mock_smsir):
        """Test sending an SMS with a verification code."""
        send_sms_notification(self.user1.phone_number, {"code": "12345"})
        mock_smsir.assert_called_once_with(
            api_key="dummy_api_key", line_number=settings.SMSIR_LINE_NUMBER
        )
        instance = mock_smsir.return_value
        instance.send_bulk.assert_called_once_with(
            "Your verification code is: 12345", [str(self.user1.phone_number)]
        )

    @override_settings(SMSIR_API_KEY="dummy_api_key")
    @patch("notifications.tasks.SmsIr")
    def test_send_sms_notification_for_tournament(self, mock_smsir):
        """Test sending an SMS for a tournament notification."""
        context = {"tournament_name": "Test Tourney", "room_id": "room123"}
        send_sms_notification(self.user1.phone_number, context)
        instance = mock_smsir.return_value
        instance.send_bulk.assert_called_once_with(
            "You have joined the tournament: Test Tourney. Room ID: room123",
            [str(self.user1.phone_number)],
        )

    @patch("notifications.tasks.send_mail")
    def test_send_email_notification(self, mock_send_mail):
        """Test sending an email notification."""
        context = {"test": "data"}
        send_email_notification(
            self.user1.email, "Test Subject", context
        )
        mock_send_mail.assert_called_once()
        args, kwargs = mock_send_mail.call_args
        self.assertEqual(args[0], "Test Subject")  # subject
        self.assertEqual(args[2], settings.EMAIL_HOST_USER)  # from_email
        self.assertEqual(args[3], [self.user1.email])  # recipient_list
        self.assertIn("<html>", kwargs["html_message"])  # html_message

    @patch("notifications.tasks.send_email_notification.delay")
    @patch("notifications.tasks.send_sms_notification.delay")
    def test_send_tournament_credentials(self, mock_send_sms, mock_send_email):
        """Test the task that sends credentials for a tournament."""
        game = Game.objects.create(name="Test Game")
        tournament = Tournament.objects.create(
            name="T1",
            game=game,
            start_date="2025-01-01T00:00:00Z",
            end_date="2025-01-02T00:00:00Z",
        )
        match = Match.objects.create(
            tournament=tournament,
            participant1_user=self.user1,
            participant2_user=self.user2,
            round=1,
            room_id="room1",
            password="pass",
            match_type="individual",
        )

        send_tournament_credentials(tournament.id)

        # It should be called once for each user
        self.assertEqual(mock_send_email.call_count, 2)
        self.assertEqual(mock_send_sms.call_count, 2)

        # Find the call for each user, regardless of order
        email_call_for_user1 = next(
            call for call in mock_send_email.call_args_list if call[0][0] == self.user1.email
        )
        email_call_for_user2 = next(
            call for call in mock_send_email.call_args_list if call[0][0] == self.user2.email
        )
        sms_call_for_user1 = next(
            call for call in mock_send_sms.call_args_list if call[0][0] == str(self.user1.phone_number)
        )
        sms_call_for_user2 = next(
            call for call in mock_send_sms.call_args_list if call[0][0] == str(self.user2.phone_number)
        )

        # Assertions for user1's notification
        context_user1 = email_call_for_user1[0][2]
        self.assertEqual(context_user1["tournament_name"], "T1")
        self.assertEqual(context_user1["room_id"], "room1")
        self.assertEqual(context_user1["password"], "pass")
        self.assertEqual(context_user1["opponent_name"], self.user2.username)
        self.assertEqual(sms_call_for_user1[0][1], context_user1) # Check context is the same for SMS

        # Assertions for user2's notification
        context_user2 = email_call_for_user2[0][2]
        self.assertEqual(context_user2["opponent_name"], self.user1.username)
        self.assertEqual(sms_call_for_user2[0][1], context_user2)

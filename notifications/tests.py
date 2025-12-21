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

    @override_settings(SMSIR_API_KEY="dummy_api_key", SMSIR_OTP_TEMPLATE_ID="123")
    @patch("notifications.tasks.SmsIr")
    def test_send_sms_notification_with_code(self, mock_smsir):
        """Test sending an SMS with a verification code."""
        parameters = {"Code": "12345"}
        send_sms_notification(
            self.user1.phone_number, settings.SMSIR_OTP_TEMPLATE_ID, parameters
        )
        mock_smsir.assert_called_once_with(
            api_key="dummy_api_key", line_number=settings.SMSIR_LINE_NUMBER
        )
        instance = mock_smsir.return_value
        expected_payload = {
            "ParameterArray": [{"Parameter": "Code", "ParameterValue": "12345"}],
            "Mobile": str(self.user1.phone_number),
            "TemplateId": "123",
        }
        instance.ultra_fast_send.assert_called_once_with(expected_payload)

    @override_settings(
        SMSIR_API_KEY="dummy_api_key", SMSIR_TOURNAMENT_TEMPLATE_ID="456"
    )
    @patch("notifications.tasks.SmsIr")
    def test_send_sms_notification_for_tournament(self, mock_smsir):
        """Test sending an SMS for a tournament notification."""
        parameters = {"TournamentName": "Test Tourney", "RoomId": "room123"}
        send_sms_notification(
            self.user1.phone_number, settings.SMSIR_TOURNAMENT_TEMPLATE_ID, parameters
        )
        instance = mock_smsir.return_value
        expected_payload = {
            "ParameterArray": [
                {"Parameter": "TournamentName", "ParameterValue": "Test Tourney"},
                {"Parameter": "RoomId", "ParameterValue": "room123"},
            ],
            "Mobile": str(self.user1.phone_number),
            "TemplateId": "456",
        }
        instance.ultra_fast_send.assert_called_once_with(expected_payload)

    @patch("notifications.tasks.render_to_string")
    @patch("notifications.tasks.send_mail")
    def test_send_email_notification(self, mock_send_mail, mock_render_to_string):
        """Test sending an email notification."""
        mock_render_to_string.return_value = "<h1>Test</h1>"
        context = {"title": "Test"}
        send_email_notification(
            subject="Test Subject",
            message="This is a test message.",
            recipient_list=[self.user1.email],
            html_template="dummy.html",
            context=context,
        )

        mock_render_to_string.assert_called_once_with("dummy.html", context)
        mock_send_mail.assert_called_once()
        args, kwargs = mock_send_mail.call_args
        self.assertEqual(args[0], "Test Subject")
        self.assertEqual(args[1], "This is a test message.")
        self.assertEqual(args[2], settings.EMAIL_HOST_USER)
        self.assertEqual(args[3], [self.user1.email])
        self.assertEqual(kwargs["html_message"], "<h1>Test</h1>")

    @override_settings(SMSIR_TOURNAMENT_TEMPLATE_ID="456")
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
            call
            for call in mock_send_email.call_args_list
            if call.kwargs["recipient_list"] == [self.user1.email]
        )
        email_call_for_user2 = next(
            call
            for call in mock_send_email.call_args_list
            if call.kwargs["recipient_list"] == [self.user2.email]
        )
        sms_call_for_user1 = next(
            call
            for call in mock_send_sms.call_args_list
            if call[0][0] == str(self.user1.phone_number)
        )
        sms_call_for_user2 = next(
            call
            for call in mock_send_sms.call_args_list
            if call[0][0] == str(self.user2.phone_number)
        )

        # Assertions for user1's notification
        kwargs_user1 = email_call_for_user1.kwargs
        self.assertEqual(kwargs_user1["subject"], "اطلاعات مسابقه شما")
        self.assertIn("room1", kwargs_user1["message"])
        self.assertEqual(
            kwargs_user1["html_template"], "notifications/email/tournament_joined.html"
        )
        context_user1 = kwargs_user1["context"]
        self.assertEqual(context_user1["opponent_name"], self.user2.username)

        sms_args_user1 = sms_call_for_user1.args
        self.assertEqual(sms_args_user1[1], "456")  # Check template ID
        self.assertEqual(sms_args_user1[2]["OpponentName"], self.user2.username)

        # Assertions for user2's notification
        kwargs_user2 = email_call_for_user2.kwargs
        context_user2 = kwargs_user2["context"]
        self.assertEqual(context_user2["opponent_name"], self.user1.username)

        sms_args_user2 = sms_call_for_user2.args
        self.assertEqual(sms_args_user2[2]["OpponentName"], self.user1.username)

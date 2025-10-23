"""
Tests for the user services in users/services.py.
These tests cover logic such as OTP generation/validation,
team invitations, and other user-related business logic.
"""
import pytest
from unittest.mock import patch, call
from freezegun import freeze_time
from datetime import timedelta
from django.utils import timezone

from users.services import (
    send_otp_service,
    verify_otp_service,
    invite_member_service,
    respond_to_invitation_service,
    leave_team_service,
    remove_member_service,
    ApplicationError,
)
from users.models import User, OTP, Team, TeamInvitation


@pytest.fixture
def user_with_phone_and_email(user_factory):
    """Creates a user with both a phone number and an email."""
    return user_factory(
        username="multifactor_user",
        phone_number="+989121112233",
        email="test@example.com",
    )


@pytest.fixture
def team_setup(user_factory):
    """Creates a team with a captain and a member."""
    captain = user_factory(username="captain", phone_number="+989123456777")
    member = user_factory(username="member", phone_number="+989123456788")
    team = Team.objects.create(name="The A-Team", captain=captain)
    team.members.add(member)
    return team, captain, member


@pytest.mark.django_db
@patch("users.services.send_sms_notification.delay")
@patch("users.services.send_email_notification.delay")
class TestOTPService:
    def test_send_otp_via_phone(
        self, mock_email, mock_sms, user_with_phone_and_email
    ):
        """
        GIVEN a user identifier (phone number)
        WHEN the send_otp_service is called
        THEN an OTP is created and sent via SMS.
        """
        send_otp_service(identifier=str(user_with_phone_and_email.phone_number))
        otp = OTP.objects.get(user=user_with_phone_and_email)

        mock_sms.assert_called_once_with(
            str(user_with_phone_and_email.phone_number), {"code": otp.code}
        )

    def test_send_otp_via_email(
        self, mock_email, mock_sms, user_with_phone_and_email
    ):
        """
        GIVEN a user identifier (email)
        WHEN the send_otp_service is called
        THEN an OTP is created and sent via email.
        """
        send_otp_service(identifier=user_with_phone_and_email.email)
        otp = OTP.objects.get(user=user_with_phone_and_email)

        mock_email.assert_called_once()

    def test_verify_otp_success(self, mock_email, mock_sms, default_user):
        """
        GIVEN a valid OTP
        WHEN the verify_otp_service is called
        THEN it should return JWT tokens and deactivate the OTP.
        """
        otp = OTP.objects.create(user=default_user, code="123456")
        result = verify_otp_service(
            identifier=str(default_user.phone_number), code="123456"
        )

        assert "refresh" in result
        assert "access" in result
        otp.refresh_from_db()
        assert not otp.is_active

    def test_verify_otp_expired(self, mock_email, mock_sms, default_user):
        """
        GIVEN an expired OTP
        WHEN the verify_otp_service is called
        THEN it should raise an ApplicationError.
        """
        with freeze_time(timezone.now() - timedelta(minutes=6)):
            OTP.objects.create(user=default_user, code="123456")

        with pytest.raises(ApplicationError, match="OTP expired."):
            verify_otp_service(identifier=str(default_user.phone_number), code="123456")

    def test_verify_otp_invalid_code(self, mock_email, mock_sms, default_user):
        """
        GIVEN an invalid OTP
        WHEN the verify_otp_service is called
        THEN it should raise an ApplicationError.
        """
        OTP.objects.create(user=default_user, code="123456")
        with pytest.raises(ApplicationError, match="Invalid OTP."):
            verify_otp_service(identifier=str(default_user.phone_number), code="654321")


@pytest.mark.django_db
class TestTeamManagementService:
    def test_invite_member_success(self, team_setup, user_factory):
        """
        GIVEN a team captain and a user to invite
        WHEN the captain invites the user
        THEN a TeamInvitation object should be created.
        """
        team, captain, _ = team_setup
        new_user = user_factory(username="newbie")
        invite_member_service(team=team, from_user=captain, to_user_id=new_user.id)
        assert TeamInvitation.objects.filter(team=team, to_user=new_user).exists()

    def test_invite_member_not_captain(self, team_setup, user_factory):
        """
        GIVEN a regular team member
        WHEN they try to invite a user
        THEN an ApplicationError should be raised.
        """
        team, _, member = team_setup
        new_user = user_factory(username="newbie")
        with pytest.raises(ApplicationError, match="Only the team captain can invite"):
            invite_member_service(team=team, from_user=member, to_user_id=new_user.id)

    def test_respond_to_invitation_accept(self, team_setup, user_factory):
        """
        GIVEN a pending invitation
        WHEN the invited user accepts it
        THEN they should be added to the team's members.
        """
        team, captain, _ = team_setup
        invitee = user_factory(username="invitee")
        invitation = TeamInvitation.objects.create(
            team=team, from_user=captain, to_user=invitee
        )

        respond_to_invitation_service(
            invitation_id=invitation.id, user=invitee, status="accepted"
        )
        team.refresh_from_db()
        assert invitee in team.members.all()

    def test_leave_team_success(self, team_setup):
        """
        GIVEN a team member
        WHEN they choose to leave the team
        THEN they should be removed from the team's members.
        """
        team, _, member = team_setup
        leave_team_service(team=team, user=member)
        team.refresh_from_db()
        assert member not in team.members.all()

    def test_captain_cannot_leave_team(self, team_setup):
        """
        GIVEN a team captain
        WHEN they try to leave the team
        THEN an ApplicationError should be raised.
        """
        team, captain, _ = team_setup
        with pytest.raises(ApplicationError, match="The captain cannot leave the team"):
            leave_team_service(team=team, user=captain)

    def test_captain_remove_member_success(self, team_setup):
        """
        GIVEN a team captain and a member
        WHEN the captain removes the member
        THEN the member should be removed from the team.
        """
        team, captain, member = team_setup
        remove_member_service(team=team, captain=captain, member_id=member.id)
        team.refresh_from_db()
        assert member not in team.members.all()

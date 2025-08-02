import random
import string

from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from notifications.tasks import send_email_notification, send_sms_notification
from .models import OTP, User, Team, TeamInvitation


class ApplicationError(Exception):
    pass


def send_otp_service(phone_number=None, email=None):
    """
    Finds the user and sends an OTP code.
    """
    if not phone_number and not email:
        raise ApplicationError("Phone number or email is required.")

    user = None
    if phone_number:
        try:
            user = User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            pass
    if email and not user:
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise ApplicationError("User not found.")
    if not user:
        raise ApplicationError("User not found.")

    otp_code = "".join(random.choices(string.digits, k=6))
    otp = OTP.objects.create(user=user, code=otp_code)

    # Send SMS
    if user.phone_number:
        send_sms_notification.delay(str(user.phone_number), {"code": otp.code})
    # Send Email
    if user.email:
        send_email_notification.delay(user.email, "OTP Code", {"code": otp.code})

    return otp


def verify_otp_service(phone_number=None, email=None, code=None):
    """
    Verifies the OTP code and returns JWT tokens if valid.
    """
    if not code or (not phone_number and not email):
        raise ApplicationError("Phone number or email and code are required.")

    user = None
    if phone_number:
        try:
            user = User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            pass
    if email and not user:
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise ApplicationError("User not found.")
    if not user:
        raise ApplicationError("User not found.")

    try:
        otp = OTP.objects.get(user=user, code=code, is_active=True)
        if (timezone.now() - otp.created_at).total_seconds() > 300:  # 5 minutes
            otp.is_active = False
            otp.save()
            raise ApplicationError("OTP expired.")

        otp.is_active = False
        otp.save()

        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }
    except OTP.DoesNotExist:
        raise ApplicationError("Invalid OTP.")


def invite_member_service(team: Team, from_user: User, to_user_id: int):
    """
    Invites a user to a team.
    """
    if from_user != team.captain:
        raise ApplicationError("Only the team captain can invite members.")

    try:
        to_user = User.objects.get(id=to_user_id)
    except User.DoesNotExist:
        raise ApplicationError("User not found.")

    if to_user in team.members.all():
        raise ApplicationError("User is already a member of the team.")

    invitation, created = TeamInvitation.objects.get_or_create(
        from_user=from_user, to_user=to_user, team=team
    )
    if not created:
        raise ApplicationError("Invitation already sent.")

    return invitation


def respond_to_invitation_service(invitation_id: int, user: User, status: str):
    """
    Responds to a team invitation.
    """
    try:
        invitation = TeamInvitation.objects.get(id=invitation_id, to_user=user)
    except TeamInvitation.DoesNotExist:
        raise ApplicationError("Invitation not found.")

    if status == "accepted":
        invitation.status = "accepted"
        invitation.team.members.add(user)
        invitation.save()
    elif status == "rejected":
        invitation.status = "rejected"
        invitation.save()
    else:
        raise ApplicationError("Invalid status.")

    return invitation


def leave_team_service(team: Team, user: User):
    """
    Allows a user to leave a team.
    """
    if user not in team.members.all():
        raise ApplicationError("You are not a member of this team.")
    if user == team.captain:
        raise ApplicationError(
            "The captain cannot leave the team. Please transfer captaincy first."
        )

    team.members.remove(user)


def remove_member_service(team: Team, captain: User, member_id: int):
    """
    Allows a captain to remove a member from a team.
    """
    if captain != team.captain:
        raise ApplicationError("Only the team captain can remove members.")

    try:
        member = User.objects.get(id=member_id)
    except User.DoesNotExist:
        raise ApplicationError("User not found.")

    if member not in team.members.all():
        raise ApplicationError("User is not a member of the team.")

    if member == team.captain:
        raise ApplicationError("The captain cannot be removed from the team.")

    team.members.remove(member)

import random
import string

from django.core.cache import cache
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from notifications.tasks import send_email_notification, send_sms_notification

from .models import OTP, Team, TeamInvitation, TeamMembership, User


class ApplicationError(Exception):
    pass


def send_otp_service(identifier=None):
    """
    Generates an OTP and sends it to the user's identifier (phone or email).
    The OTP is stored in the cache.
    """
    if not identifier:
        raise ApplicationError("Identifier (email or phone number) is required.")

    otp_code = "".join(random.choices(string.digits, k=6))

    # Store OTP in cache for 5 minutes
    cache.set(f"otp_{identifier}", otp_code, timeout=300)

    # Send SMS or Email based on identifier type
    if "@" in identifier:
        try:
            user = User.objects.get(email=identifier)
            if not user.is_phone_verified:
                raise ApplicationError(
                    "Please verify your phone number before using email to log in."
                )
        except User.DoesNotExist:
            raise ApplicationError(
                "No user found with this email. Please sign up with your phone number first."
            )

        send_email_notification.delay(
            identifier,
            "Your Verification Code",
            "notifications/email/login_verification_email.html",
            {"code": otp_code},
        )
    else:
        send_sms_notification.delay(identifier, {"code": otp_code})


def verify_otp_service(identifier=None, code=None):
    """
    Verifies the OTP. If valid, logs in the user or creates a new one.
    """
    if not code:
        raise ApplicationError("Code is required.")
    if not identifier:
        raise ApplicationError("Identifier (email or phone number) is required.")

    cached_otp = cache.get(f"otp_{identifier}")
    if not cached_otp or cached_otp != code:
        raise ApplicationError("Invalid OTP.")

    # OTP is valid, clear it from cache
    cache.delete(f"otp_{identifier}")

    # Determine if identifier is email or phone
    is_email = "@" in identifier
    query_field = "email" if is_email else "phone_number"

    # Get or create the user
    user, created = User.objects.get_or_create(
        **{query_field: identifier},
        defaults={"username": identifier}  # Use identifier as username for simplicity
    )

    if created:
        user.set_unusable_password()
        user.save()

    # If the user is verifying with a phone number, mark as verified
    if not is_email and not user.is_phone_verified:
        user.is_phone_verified = True
        user.save(update_fields=["is_phone_verified"])

    return user


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
        TeamMembership.objects.create(user=user, team=invitation.team)
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

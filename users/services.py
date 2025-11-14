import random
import string

from django.core.cache import cache
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from notifications.tasks import send_email_notification, send_sms_notification

from .models import OTP, User


class ApplicationError(Exception):
    pass


def send_otp_service(identifier=None):
    """
    Generates an OTP, stores it in the database, and sends it to the user's identifier (phone or email).
    """
    if not identifier:
        raise ApplicationError("Identifier (email or phone number) is required.")

    otp_code = "".join(random.choices(string.digits, k=6))

    # Invalidate previous OTPs for this identifier
    OTP.objects.filter(identifier=identifier, is_used=False).update(is_used=True)

    # Determine if identifier is email or phone
    is_email = "@" in identifier
    user = None
    if is_email:
        try:
            user = User.objects.get(email=identifier)
            if not user.is_phone_verified:
                raise ApplicationError("Please verify your phone number before using email to log in.")
        except User.DoesNotExist:
            raise ApplicationError("No user found with this email. Please sign up with your phone number first.")
    else:
        user = User.objects.filter(phone_number=identifier).first()

    # Create and save the new OTP
    OTP.objects.create(
        identifier=identifier,
        code=otp_code,
        user=user
    )

    # Send SMS or Email based on identifier type
    if is_email:
        plain_message = f"Your verification code is: {otp_code}"
        send_email_notification.delay(
            subject="Your Verification Code",
            message=plain_message,
            recipient_list=[identifier],
        )
    else:
        send_sms_notification.delay(identifier, {"code": otp_code})


def verify_otp_service(identifier=None, code=None):
    """
    Verifies the OTP from the database. If valid, logs in the user or creates a new one.
    """
    if not code:
        raise ApplicationError("Code is required.")
    if not identifier:
        raise ApplicationError("Identifier (email or phone number) is required.")

    try:
        otp = OTP.objects.get(identifier=identifier, code=code, is_used=False)
    except OTP.DoesNotExist:
        raise ApplicationError("Invalid OTP.")

    if otp.is_expired:
        raise ApplicationError("OTP has expired.")

    # Mark OTP as used
    otp.is_used = True
    otp.save()

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

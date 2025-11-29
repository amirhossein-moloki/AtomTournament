from rest_framework.throttling import UserRateThrottle


class VeryStrictThrottle(UserRateThrottle):
    """
    Limits requests to 1 per minute.
    Used for highly sensitive operations like OTP requests or withdrawals.
    """
    scope = 'very_strict'


class StrictThrottle(UserRateThrottle):
    """
    Limits requests to 10 per minute.
    Used for sensitive operations like creating teams or updating user profiles.
    """
    scope = 'strict'


class MediumThrottle(UserRateThrottle):
    """
    Limits requests to 100 per 10 minutes.
    Used for general authenticated actions like listing resources.
    """
    scope = 'medium'


class RelaxedThrottle(UserRateThrottle):
    """
    Limits requests to 500 per hour.
    Used for non-sensitive, public-facing endpoints.
    """
    scope = 'relaxed'

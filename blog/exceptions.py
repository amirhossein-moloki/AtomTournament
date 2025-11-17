from django.conf import settings
from rest_framework.views import exception_handler
from django.http import Http404
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework import status

def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF.
    """
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # Now, customize the response data.
    if response is not None:
        return response

    if isinstance(exc, Http404):
        return Response(
            {"error": "Not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    if isinstance(exc, PermissionDenied):
        return Response(
            {"error": "Permission denied."},
            status=status.HTTP_403_FORBIDDEN
        )

    # For unhandled exceptions, return a generic 500 error in production
    if not settings.DEBUG:
        return Response(
            {"error": "An unexpected error occurred."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # In DEBUG mode, let Django's default error page handle the exception
    return None

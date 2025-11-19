from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404
from rest_framework.exceptions import APIException, NotAuthenticated, PermissionDenied, NotFound
from django.conf import settings


def custom_exception_handler(exc, context):
    """
    مدیریت کننده خطای سفارشی برای ویوهای DRF.
    این تابع خطاهای استاندارد DRF و خطاهای عمومی پایتون را مدیریت کرده
    و یک پاسخ JSON استاندارد با پیام فارسی برمی‌گرداند.
    """
    # فراخوانی handler پیش‌فرض DRF برای گرفتن پاسخ اولیه
    response = exception_handler(exc, context)

    # تعیین جزئیات پیام خطا بر اساس نوع استثنا
    if isinstance(exc, NotAuthenticated):
        detail = "احراز هویت انجام نشده است. لطفاً ابتدا وارد حساب کاربری خود شوید."
        error_code = "not_authenticated"
        status_code = status.HTTP_401_UNAUTHORIZED
    elif isinstance(exc, PermissionDenied):
        detail = "شما دسترسی لازم برای انجام این عملیات را ندارید."
        error_code = "permission_denied"
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, NotFound) or isinstance(exc, Http404):
        detail = "موجودیت درخواستی یافت نشد."
        error_code = "not_found"
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, APIException):
        # برای سایر خطاهای DRF، از جزئیات خود خطا استفاده می‌شود
        detail = exc.detail
        error_code = exc.get_codes()
        status_code = exc.status_code
    else:
        # برای خطاهای پیش‌بینی نشده (خطاهای داخلی سرور)
        # در حالت DEBUG، جزئیات خطا را نمایش می‌دهیم تا به دیباگ کمک کند
        if settings.DEBUG:
            detail = f"خطای داخلی سرور: {str(exc)}"
        else:
            detail = "یک خطای پیش‌بینی نشده در سرور رخ داده است. لطفاً بعداً تلاش کنید."
        error_code = "internal_server_error"
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    # ساخت پاسخ سفارشی
    custom_response_data = {
        'detail': detail,
        'error_code': error_code
    }

    return Response(custom_response_data, status=status_code)

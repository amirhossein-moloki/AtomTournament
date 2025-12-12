import re
import os
import mimetypes
from django.conf import settings
from django.core.exceptions import ValidationError


def validate_file(value):
    """
    Validates file size, extension and content type.
    """
    # TODO: For enhanced security and scalability, migrate to a cloud-based storage
    # solution like AWS S3. Utilize pre-signed URLs for direct client-side uploads.
    # This approach offloads the file handling from the application server, improving
    # performance and security by preventing malicious file uploads from reaching the server.

    filesize = value.size
    max_size = settings.MAX_UPLOAD_SIZE_BYTES
    if filesize > max_size:
        if max_size < 1024 * 1024:
            max_size_str = f"{max_size / 1024:.1f} کیلوبایت"
        else:
            max_size_str = f"{max_size / (1024 * 1024):.1f} مگابایت"
        raise ValidationError(f"حجم فایل شما بیشتر از {max_size_str} است. لطفا یک فایل کوچکتر آپلود کنید.")

    allowed_extensions = settings.ALLOWED_UPLOAD_EXTENSIONS
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(
            f"فرمت فایل ‘{ext}’ پشتیبانی نمی‌شود. لطفا یکی از فرمت‌های مجاز را امتحان کنید: {', '.join(allowed_extensions)}"
        )

    # Content type validation
    content_type = getattr(value, 'content_type', mimetypes.guess_type(value.name)[0])
    if content_type not in settings.ALLOWED_UPLOAD_CONTENT_TYPES:
        raise ValidationError(
            f"نوع فایل ‘{content_type}’ پشتیبانی نمی‌شود."
        )


def validate_sheba(value):
    """
    Validates a SHEBA number.
    A valid SHEBA number starts with 'IR' followed by 24 digits.
    """
    if not re.match(r'^IR\d{24}$', value):
        raise ValidationError('شماره شبا نامعتبر است. باید با IR شروع شده و شامل ۲۴ عدد باشد.')


def validate_card_number(value):
    """
    Validates a bank card number.
    A valid card number is a 16-digit number.
    This is a basic check and does not perform checksum validation.
    """
    if not re.match(r'^\d{16}$', value):
        raise ValidationError('شماره کارت نامعتبر است. باید ۱۶ رقم باشد.')

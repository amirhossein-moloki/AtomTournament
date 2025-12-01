import re
from django.core.exceptions import ValidationError


def validate_file(value):
    """
    Validates file size and type.
    """
    filesize = value.size
    if filesize > 10 * 1024 * 1024:
        raise ValidationError("حداکثر حجم فایل ۱۰ مگابایت است.")

    allowed_extensions = ['.jpg', '.jpeg', '.png', '.mp4', '.mov', '.webp', '.gif', '.heic', '.avif']
    ext = str(value).split('.')[-1]
    if not any(ext.lower() == ext_allowed.replace('.', '') for ext_allowed in allowed_extensions):
        raise ValidationError(f"فرمت فایل {ext} مجاز نیست.")


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

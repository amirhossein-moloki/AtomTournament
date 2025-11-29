from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

def validate_file(file):
    """
    Custom validator for file size and content type.
    """
    max_size = 1024 * 1024 * 20  # 20 MB
    allowed_content_types = [
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
        "video/mp4",
    ]

    if file.size > max_size:
        raise ValidationError(_(f"File size cannot exceed {max_size / 1024 / 1024} MB."))

    if file.content_type not in allowed_content_types:
        raise ValidationError(_("Invalid file type."))

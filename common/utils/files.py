import os
import uuid
from django.utils.text import slugify

def get_sanitized_filename(filename):
    """
    Generates a sanitized filename.
    """
    base, ext = os.path.splitext(filename)
    return f"{slugify(base)}{ext}"

def get_sanitized_upload_path(instance, filename):
    """
    Generates a sanitized, unique filename using UUID.
    """
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('uploads', filename)

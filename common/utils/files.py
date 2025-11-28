# common/utils/files.py
import os
import uuid
from django.utils.text import slugify

def get_sanitized_filename(filename):
    """
    Generates a sanitized, unique filename.

    - Splits the filename into a base name and extension.
    - Slugifies the base name to make it URL-friendly.
    - Appends a short unique ID to prevent collisions.
    - Recombines with the original extension.
    """
    base_name, extension = os.path.splitext(filename)
    slugified_name = slugify(base_name)
    unique_id = str(uuid.uuid4())[:8]

    # Ensure there's a name to work with after slugifying
    if not slugified_name:
        slugified_name = "untitled"

    return f"{slugified_name}-{unique_id}{extension}"

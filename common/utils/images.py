# common/utils/images.py

import os
import uuid
from io import BytesIO
from django.core.files.base import ContentFile
from django.utils.text import slugify
from PIL import Image
import pillow_avif  # noqa: F401 -> Registered plugin
from .files import get_sanitized_filename


def convert_image_to_avif(image_field, max_dimension=1920, quality=50, speed=6):
    """
    ورودی: یک ImageField/File
    خروجی: یک ContentFile که فرمتش AVIF هست و آماده‌ی ذخیره تو ImageField
    """

    # فایل رو با Pillow باز می‌کنیم
    img = Image.open(image_field)

    # پروفایل رنگی رو استخراج می‌کنیم تا بعدا به عکس جدید اضافه بشه
    icc_profile = img.info.get("icc_profile")

    # برای حفظ شفافیت، عکس‌هایی با مُد RGBA را تبدیل نمی‌کنیم.
    # سایر مُدها مثل CMYK یا P به RGBA تبدیل می‌شوند تا شفافیت احتمالی حفظ شود.
    if img.mode not in ("RGB", "L", "RGBA"):
        img = img.convert("RGBA")

    # اگر عرض یا ارتفاع عکس خیلی بزرگ بود، کوچیکش کن
    if img.width > max_dimension or img.height > max_dimension:
        img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

    # توی buffer به فرمت AVIF ذخیره می‌کنیم
    buffer = BytesIO()
    save_kwargs = {
        "format": "AVIF",
        "quality": quality,
        "speed": speed,
        "strip": True,
    }
    if icc_profile:
        save_kwargs["icc_profile"] = icc_profile

    img.save(buffer, **save_kwargs)
    buffer.seek(0)

    # اسم فایل رو .avif می‌کنیم
    original_name = getattr(image_field, 'name', 'untitled.avif')
    sanitized_name = get_sanitized_filename(original_name)

    # Ensure the final name has a .avif extension
    base_name, _ = os.path.splitext(sanitized_name)
    new_name = f"{base_name}.avif"

    return ContentFile(buffer.read(), name=new_name)

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


def create_image_variants(image_field, main_size=(1920, 1920), thumb_size=(400, 400), quality=50, speed=6):
    """
    Creates multiple versions (variants) of an image.
    Returns a tuple: (main_image_content, variants_dict)
    """
    variants = {}

    # 1. Create and save the main optimized AVIF image
    main_image_content = convert_image_to_avif(
        image_field, max_dimension=main_size[0], quality=quality, speed=speed
    )

    # 2. Create the thumbnail variant
    # We need to re-open the original image to create a smaller version
    image_field.seek(0)
    img = Image.open(image_field)

    # Ensure it's in a compatible mode before creating the thumbnail
    if img.mode not in ("RGB", "L", "RGBA"):
        img = img.convert("RGBA")

    img.thumbnail(thumb_size, Image.Resampling.LANCZOS)

    thumb_buffer = BytesIO()
    img.save(thumb_buffer, format="AVIF", quality=quality-10, speed=speed+1) # Lower quality for smaller size
    thumb_buffer.seek(0)

    # Generate a unique name for the thumbnail
    base_name, _ = os.path.splitext(main_image_content.name)
    thumb_name = f"{base_name}_thumb.avif"

    # Save the thumbnail to storage
    thumb_storage_key = os.path.join(os.path.dirname(main_image_content.name), thumb_name)
    thumb_url = default_storage.save(thumb_storage_key, ContentFile(thumb_buffer.read()))

    variants['thumbnail'] = default_storage.url(thumb_url)

    return main_image_content, variants

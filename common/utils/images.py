# common/utils/images.py

from io import BytesIO
from django.core.files.base import ContentFile
from PIL import Image
import pillow_avif  # noqa: F401 -> Registered plugin


def convert_image_to_avif(image_field, max_width=1920, quality=75):
    """
    ورودی: یک ImageField/File
    خروجی: یک ContentFile که فرمتش AVIF هست و آماده‌ی ذخیره تو ImageField
    """

    # فایل رو با Pillow باز می‌کنیم
    img = Image.open(image_field)

    # به RGB تبدیل می‌کنیم (برای PNG/transparent و غیره)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    # اگر خیلی بزرگ بود، کوچیکش کن
    if img.width > max_width:
        ratio = max_width / float(img.width)
        new_height = int(float(img.height) * ratio)
        img = img.resize((max_width, new_height), Image.LANCZOS)

    # توی buffer به فرمت AVIF ذخیره می‌کنیم
    buffer = BytesIO()
    # Note: `method=6` is for WEBP, AVIF has different params. Using defaults for now.
    img.save(buffer, format="AVIF", quality=quality)
    buffer.seek(0)

    # اسم فایل رو .avif می‌کنیم
    original_name = getattr(image_field, 'name', 'untitled.avif')
    if "." in original_name:
        base_name = original_name.rsplit(".", 1)[0]
    else:
        base_name = original_name

    new_name = base_name + ".avif"

    return ContentFile(buffer.read(), name=new_name)

# common/utils/images.py

from io import BytesIO
from django.core.files.base import ContentFile
from PIL import Image


def convert_image_to_webp(image_field, max_width=1920, quality=80):
    """
    ورودی: یک ImageField/File
    خروجی: یک ContentFile که فرمتش WebP هست و آماده‌ی ذخیره تو ImageField
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

    # توی buffer به فرمت WEBP ذخیره می‌کنیم
    buffer = BytesIO()
    img.save(buffer, format="WEBP", quality=quality, method=6)
    buffer.seek(0)

    # اسم فایل رو .webp می‌کنیم
    original_name = image_field.name
    if "." in original_name:
        base_name = original_name.rsplit(".", 1)[0]
    else:
        base_name = original_name

    new_name = base_name + ".webp"

    return ContentFile(buffer.read(), name=new_name)

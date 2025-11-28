# common/utils/images.py

from io import BytesIO
from django.core.files.base import ContentFile
from PIL import Image
import pillow_avif  # noqa: F401 -> Registered plugin


def convert_image_to_avif(image_field, max_width=1920, quality=75, speed=4):
    """
    ورودی: یک ImageField/File
    خروجی: یک ContentFile که فرمتش AVIF هست و آماده‌ی ذخیره تو ImageField
    """

    # فایل رو با Pillow باز می‌کنیم
    img = Image.open(image_field)

    # برای حفظ شفافیت، عکس‌هایی با مُد RGBA را تبدیل نمی‌کنیم.
    # سایر مُدها مثل CMYK یا P به RGBA تبدیل می‌شوند تا شفافیت احتمالی حفظ شود.
    if img.mode not in ("RGB", "L", "RGBA"):
        img = img.convert("RGBA")

    # اگر خیلی بزرگ بود، کوچیکش کن
    if img.width > max_width:
        ratio = max_width / float(img.width)
        new_height = int(float(img.height) * ratio)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

    # توی buffer به فرمت AVIF ذخیره می‌کنیم
    buffer = BytesIO()
    # speed=4 provides a good balance between compression time and file size.
    img.save(buffer, format="AVIF", quality=quality, speed=speed, strip=True)
    buffer.seek(0)

    # اسم فایل رو .avif می‌کنیم
    original_name = getattr(image_field, 'name', 'untitled.avif')
    if "." in original_name:
        base_name = original_name.rsplit(".", 1)[0]
    else:
        base_name = original_name

    new_name = base_name + ".avif"

    return ContentFile(buffer.read(), name=new_name)

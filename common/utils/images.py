# common/utils/images.py

from io import BytesIO
from django.core.files.base import ContentFile
from PIL import Image
import pillow_avif  # noqa: F401 -> Registered plugin


def convert_image_to_avif(image_field, max_dimension=1920, quality=75, speed=4):
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
    if "." in original_name:
        base_name = original_name.rsplit(".", 1)[0]
    else:
        base_name = original_name

    new_name = base_name + ".avif"

    return ContentFile(buffer.read(), name=new_name)

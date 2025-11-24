from celery import shared_task
from django.apps import apps
from django.core.files.storage import default_storage
from .utils.images import convert_image_to_avif
import os

@shared_task(bind=True, max_retries=3)
def convert_image_to_avif_task(self, app_label, model_name, instance_pk, field_name):
    """
    یک وظیفه Celery برای تبدیل ناهمگام یک فیلد تصویر به فرمت AVIF.
    """
    try:
        # پیدا کردن مدل و آبجکت مورد نظر از دیتابیس
        Model = apps.get_model(app_label, model_name)
        instance = Model.objects.get(pk=instance_pk)

        image_field = getattr(instance, field_name)

        # اگر فایلی وجود نداشت یا از قبل AVIF بود، کاری انجام نده
        if not image_field or not image_field.name or image_field.name.lower().endswith('.avif'):
            return f"No action needed for {model_name} {instance_pk}."

        original_path = image_field.path

        # 1. فایل اصلی را از حافظه بخوان
        with image_field.open('rb') as original_file:
            # 2. تبدیل به AVIF در حافظه
            avif_content = convert_image_to_avif(original_file)
            new_storage_key = os.path.splitext(image_field.name)[0] + '.avif'

        # 3. فایل جدید را ذخیره کن
        saved_path = default_storage.save(new_storage_key, avif_content)

        # 4. مدل را آپدیت کن
        setattr(instance, field_name, saved_path)
        instance.save(update_fields=[field_name])

        # 5. فایل اصلی را (در صورت متفاوت بودن) حذف کن
        if saved_path != original_path and default_storage.exists(original_path):
             default_storage.delete(original_path)

        return f"Successfully converted image for {model_name} {instance_pk}."

    except Model.DoesNotExist:
        # اگر آبجکت قبل از اجرای تسک حذف شده بود، مشکلی نیست
        return f"{model_name} with pk {instance_pk} not found. Skipping."
    except Exception as exc:
        # در صورت بروز خطا، Celery تسک را دوباره تلاش می‌کند (تا 3 بار)
        raise self.retry(exc=exc, countdown=60) # 60 ثانیه بعد دوباره تلاش کن

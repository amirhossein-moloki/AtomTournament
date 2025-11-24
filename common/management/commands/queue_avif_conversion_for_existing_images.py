# common/management/commands/queue_avif_conversion_for_existing_images.py

from django.core.management.base import BaseCommand
from common.tasks import convert_image_to_avif_task
from django.apps import apps
from django.db.models import ImageField

class Command(BaseCommand):
    help = 'تمام تصاویر موجود در سیستم را برای تبدیل به فرمت AVIF در صف قرار می‌دهد.'

    def handle(self, *args, **options):
        self.stdout.write("شروع اسکن مدل‌ها برای یافتن فیلدهای تصویر...")

        # لیستی از مدل‌هایی که می‌خواهیم اسکن شوند
        # می‌توانید این لیست را برای محدود کردن اسکن ویرایش کنید
        models_to_scan = apps.get_models()

        total_tasks_queued = 0

        for model in models_to_scan:
            image_fields = [f for f in model._meta.get_fields() if isinstance(f, ImageField)]

            if not image_fields:
                continue

            self.stdout.write(f"  اسکن مدل: {model.__name__}")

            for instance in model.objects.all():
                for field in image_fields:
                    field_name = field.name
                    try:
                        image_field = getattr(instance, field_name)

                        # اگر فیلد تصویر مقدار داشت و هنوز AVIF نشده بود
                        if image_field and hasattr(image_field, 'name') and image_field.name and not image_field.name.lower().endswith('.avif'):
                            self.stdout.write(f"    -> در صف قرار دادن تسک برای {model.__name__} ID: {instance.pk}, فیلد: {field_name}")
                            convert_image_to_avif_task.delay(
                                app_label=model._meta.app_label,
                                model_name=model._meta.model_name,
                                instance_pk=instance.pk,
                                field_name=field_name
                            )
                            total_tasks_queued += 1

                    except Exception as e:
                        self.stderr.write(self.style.ERROR(f"خطا در پردازش {model.__name__} ID: {instance.pk}, فیلد: {field_name}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"عملیات با موفقیت انجام شد. تعداد کل تسک‌های در صف قرار گرفته: {total_tasks_queued}"))

# گزارش تحلیل و رفع اشکال ماژول `blog`

## ۱. تشخیص سطح بالا

مشکل اصلی در ماژول `blog` ناهماهنگی بین مدل‌های جنگو، سریالایزرها و اسکیمای پایگاه داده PostgreSQL بود. این ناهماهنگی منجر به خطاهای `500 Internal Server Error` هنگام ایجاد پست جدید می‌شد، زیرا پایگاه داده اجازه درج مقدار `NULL` در ستون‌هایی مانند `likes_count` را نمی‌داد، در حالی که کد برنامه مقداری برای آن ارسال نمی‌کرد. همچنین، فیلدهایی که باید توسط بک‌اند محاسبه می‌شدند (مانند `reading_time_sec`) به اشتباه از کلاینت درخواست می‌شدند و باعث خطای اعتبارسنجی (`Validation Error`) می‌شدند.

## ۲. لیست دقیق مشکلات

- **مشکل ۱: `IntegrityError` در پایگاه داده**
  - **فایل:** `blog/models.py` و اسکیمای `blog_post` در PostgreSQL
  - **شرح:** ستون‌های `likes_count` و `views_count` در پایگاه داده با محدودیت `NOT NULL` تعریف شده بودند، اما هیچ مقدار پیش‌فرضی (`DEFAULT`) برای آن‌ها تنظیم نشده بود. مدل جنگو `default=0` را مشخص کرده بود، اما این تغییر به درستی در یک مایگریشن قبلی اعمال نشده یا مایگریشن‌های متناقض باعث حذف آن شده بود. در نتیجه، هنگام اجرای `INSERT` برای یک پست جدید، چون مقادیر این فیلدها در کوئری وجود نداشت، پایگاه داده خطای `violates not-null constraint` را برمی‌گرداند.

- **مشکل ۲: خطای اعتبارسنجی `Validation Error`**
  - **فایل:** `blog/serializers.py`
  - **شرح:** سریالایزر `PostCreateUpdateSerializer` فیلد `reading_time_sec` را به عنوان یک فیلد الزامی در نظر می‌گرفت. این در حالی است که این فیلد باید به طور خودکار بر اساس محتوای پست (`content`) در بک‌اند محاسبه شود. این باعث می‌شد که کلاینت‌ها با خطای `"This field is required."` مواجه شوند.

- **مشکل ۳: تاریخچه مایگریشن نامنظم**
  - **فایل‌ها:** `blog/migrations/*`
  - **شرح:** بررسی تاریخچه مایگریشن‌ها نشان داد که فیلد `likes_count` چندین بار اضافه، حذف و دوباره اضافه شده است. این تاریخچه نامنظم می‌تواند منجر به عدم هماهنگی اسکیمای پایگاه داده در محیط‌های مختلف (توسعه، تست، پروداکشن) شود.

## ۳. کد اصلاح شده مدل `Post`

برای رفع مشکل محاسبه `reading_time_sec` و اطمینان از اینکه هرگز مقدار `NULL` نمی‌گیرد، مدل `Post` به شکل زیر اصلاح شد. مقدار پیش‌فرض `0` برای آن در نظر گرفته شد و متد `save` برای مدیریت محتوای خالی به‌روزرسانی شد.

```python
# blog/models.py

class Post(models.Model):
    # ... (other fields)
    content = models.TextField()  # Assuming RichText or Markdown is handled on the frontend
    reading_time_sec = models.PositiveIntegerField(default=0)
    # ... (other fields)
    views_count = models.PositiveIntegerField(default=0)
    likes_count = models.PositiveIntegerField(default=0)
    # ... (other fields)

    def save(self, *args, **kwargs):
        if self.content:
            words = re.findall(r'\w+', self.content)
            word_count = len(words)
            reading_time_minutes = word_count / 200  # Average reading speed
            self.reading_time_sec = int(reading_time_minutes * 60)
        else:
            self.reading_time_sec = 0
        super().save(*args, **kwargs)

```

## ۴. کد اصلاح شده سریالایزرها

سریالایزر `PostCreateUpdateSerializer` اصلاح شد تا فیلدهایی که توسط بک‌اند مدیریت می‌شوند (`likes_count`, `views_count`, `reading_time_sec`) را به صورت `read-only` در نظر بگیرد. این کار از ارسال این فیلدها توسط کلاینت و بروز خطای اعتبارسنجی جلوگیری می‌کند.

```python
# blog/serializers.py

class PostCreateUpdateSerializer(serializers.ModelSerializer):
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.all(), source='tags', required=False
    )
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', required=False
    )

    class Meta:
        model = Post
        fields = (
            'title', 'excerpt', 'content', 'status', 'visibility',
            'published_at', 'scheduled_at', 'category_id', 'series',
            'cover_media', 'seo_title', 'seo_description', 'og_image',
            'tag_ids', 'slug', 'canonical_url', 'likes_count', 'views_count',
            'reading_time_sec'
        )
        read_only_fields = (
            'likes_count', 'views_count', 'reading_time_sec'
        )
        extra_kwargs = {
            'slug': {'required': False}
        }
```

## ۵. مایگریشن‌های مورد نیاز

یک فایل مایگریشن جدید برای اعمال تغییرات در پایگاه داده ایجاد و ویرایش شد. این مایگریشن شامل سه بخش اصلی است:
۱. اجرای SQL خام برای پر کردن مقادیر `NULL` موجود در دیتابیس با `0`.
۲. تغییر ستون‌های `likes_count` و `views_count` برای افزودن `DEFAULT 0`.
۳. تغییر ستون `reading_time_sec` برای هماهنگی با مدل.

```python
# blog/migrations/0014_alter_post_reading_time_sec.py

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0013_alter_media_size_bytes"),
    ]

    operations = [
        # Backfill NULLs before altering columns to be NOT NULL
        migrations.RunSQL(
            sql='''
                UPDATE "blog_post" SET "likes_count" = 0 WHERE "likes_count" IS NULL;
                UPDATE "blog_post" SET "views_count" = 0 WHERE "views_count" IS NULL;
            ''',
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.AlterField(
            model_name="post",
            name="likes_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="post",
            name="views_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="post",
            name="reading_time_sec",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
```
**نحوه اعمال:**
```bash
python manage.py migrate blog
```

## ۶. نمونه درخواست‌ها برای `POST /api/blog/posts/`

### حداقل درخواست معتبر
این درخواست فقط شامل فیلدهای ضروری برای ایجاد یک پست در حالت پیش‌نویس (`draft`) است.

```json
{
    "title": "پست آزمایشی جدید",
    "excerpt": "این یک خلاصه کوتاه برای پست جدید است.",
    "content": "این محتوای کامل پست است که می‌تواند طولانی باشد."
}
```

### درخواست کامل با فیلدهای اختیاری
این نمونه شامل تمام فیلدهای اختیاری است که کلاینت می‌تواند ارسال کند.

```json
{
    "title": "پست کامل با تمام جزئیات",
    "slug": "full-post-with-all-details",
    "excerpt": "خلاصه‌ای جذاب از این پست که تمام جزئیات را پوشش می‌دهد.",
    "content": "محتوای پست در اینجا قرار می‌گیرد. این محتوا می‌تواند شامل Markdown یا HTML باشد...",
    "status": "published",
    "visibility": "public",
    "published_at": "2025-11-17T10:00:00Z",
    "category_id": 1,
    "tag_ids": [1, 2],
    "series": 1,
    "cover_media": 1,
    "seo_title": "عنوان سئو برای پست کامل",
    "seo_description": "توضیحات سئو برای جذب کاربران از موتورهای جستجو.",
    "og_image": 2
}
```
**نکته:** فیلدهای `likes_count`, `views_count` و `reading_time_sec` در هر دو حالت توسط سرور مدیریت شده و در پاسخ `response` نمایش داده خواهند شد.

## ۷. چک‌لیست برای تأیید صحت عملکرد

1.  **اعمال مایگریشن‌ها:** اطمینان حاصل کنید که مایگریشن جدید بدون خطا اجرا می‌شود.
    ```bash
    python manage.py migrate
    ```
2.  **تست ایجاد پست (حداقلی):** یک درخواست `POST` با حداقل بدنه JSON به ` /api/blog/posts/` ارسال کنید و بررسی کنید که پست با کد `201 Created` ایجاد شده و فیلدهای `likes_count`, `views_count` و `reading_time_sec` مقدار `0` یا مقدار محاسبه شده صحیح را داشته باشند.
3.  **تست ایجاد پست (کامل):** یک درخواست `POST` با بدنه کامل JSON ارسال کنید و بررسی کنید که تمام فیلدها به درستی ذخیره شده‌اند.
4.  **تست به‌روزرسانی پست:** یک درخواست `PUT` یا `PATCH` به ` /api/blog/posts/<slug>/` ارسال کنید و بررسی کنید که فیلدهای `read-only` (مانند `likes_count`) قابل تغییر نیستند.
5.  **بررسی مستقیم دیتابیس:** (اختیاری) اسکیمای جدول `blog_post` را در PostgreSQL با دستور `\d+ blog_post` بررسی کنید تا مطمئن شوید ستون‌های `likes_count` و `views_count` دارای `DEFAULT 0` و `NOT NULL` هستند.

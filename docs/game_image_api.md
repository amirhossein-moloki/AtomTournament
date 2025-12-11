# API مدیریت عکس‌های بازی

این راهنما توضیح می‌دهد چطور اندپوینت‌های `game-images` که در مسیر پایه‌ی `/api/tournaments/` منتشر شده‌اند را صدا بزنید و چه محدودیت‌هایی دارند.

## دسترسی و احراز هویت
- **GET /api/tournaments/game-images/** و **GET /api/tournaments/game-images/{id}/** عمومی هستند و نیازی به توکن ندارند.
- عملیات ایجاد، ویرایش و حذف (**POST**, **PUT/PATCH**, **DELETE**) فقط برای ادمین مجاز است و باید هدر احراز هویت (JWT) ارسال شود.

## فیلدها
- `id` (عدد) – شناسه رکورد (Read-only).
- `game` (عدد) – شناسه بازی مرتبط (الزامی در ساخت یا ویرایش).
- `image_type` (رشته) – نوع تصویر. مقادیر مجاز:
  - `hero_banner`
  - `cta_banner`
  - `game_image`
  - `thumbnail`
  - `icon`
  - `slider`
  - `illustration`
  - `promotional_banner`
- `image` (فایل) – تصویر قابل آپلود.
- `url` (رشته) – آدرس قابل دسترس برای تصویر (Read-only).

## لیست‌کردن تصاویر
```http
GET /api/tournaments/game-images/
Accept: application/json
```
پاسخ نمونه:
```json
[
  {
    "id": 12,
    "game": 3,
    "image_type": "thumbnail",
    "image": "http://example.com/media/uploads/games/thumb.png",
    "url": "http://example.com/media/uploads/games/thumb.png"
  }
]
```

## دریافت یک تصویر خاص
```http
GET /api/tournaments/game-images/{id}/
Accept: application/json
```

## ایجاد تصویر جدید (ادمین)
```http
POST /api/tournaments/game-images/
Authorization: Bearer <JWT>
Content-Type: multipart/form-data

image: <فایل>
game: <شناسه بازی>
image_type: <یکی از مقادیر مجاز>
```

## ویرایش تصویر (ادمین)
- **PUT** برای جایگزینی کامل:
```http
PUT /api/tournaments/game-images/{id}/
Authorization: Bearer <JWT>
Content-Type: multipart/form-data

game: <شناسه بازی>
image_type: <یکی از مقادیر مجاز>
image: <فایل>
```
- **PATCH** برای به‌روزرسانی جزئی (مثلاً فقط فایل یا نوع تصویر):
```http
PATCH /api/tournaments/game-images/{id}/
Authorization: Bearer <JWT>
Content-Type: multipart/form-data

image: <فایل یا خالی>
image_type: <اختیاری>
```

## حذف تصویر (ادمین)
```http
DELETE /api/tournaments/game-images/{id}/
Authorization: Bearer <JWT>
```

> نکته: تمامی درخواست‌های دارای فایل باید با `multipart/form-data` ارسال شوند. پاسخ‌ها مطابق ساختار `GameImageSerializer` شامل `id`، `game`، `image_type`، `image` و `url` خواهند بود.

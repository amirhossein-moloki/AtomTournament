# مستندات کامل ماژول چت

این مستندات به منظور راهنمایی تیم فرانت‌اند برای پیاده‌سازی کامل ماژول چت تهیه شده است. معماری این ماژول بر اساس REST API برای عملیات اصلی و WebSocket برای ارتباطات لحظه‌ای (real-time) بنا شده است.

## ۱. کلیات

### ۱.۱. آدرس پایه (Base URL)

تمام آدرس‌های API در این مستند، به صورت نسبی به آدرس پایه سرور هستند. برای مثال: `https://yourdomain.com/api/`

### ۱.۲. احراز هویت (Authentication)

تمام درخواست‌ها به API باید احراز هویت شده باشند. سیستم احراز هویت بر پایه توکن JWT استوار است. توکن باید در هدر `Authorization` هر درخواست به شکل زیر ارسال شود:

`Authorization: Bearer <YOUR_ACCESS_TOKEN>`

### ۱.۳. دسترسی ادمین

کاربرانی که سطح دسترسی ادمین (`is_staff=True`) دارند، به تمام مکالمات و پیام‌ها دسترسی خواهند داشت و محدودیت‌های مالکیت برای آن‌ها اعمال نمی‌شود.

## ۲. مدل‌های داده (Data Models)

### ۲.۱. User Model (Read-Only)

این مدل، اطلاعات عمومی یک کاربر را نمایش می‌دهد.

- `id` (integer): شناسه یکتای کاربر.
- `username` (string): نام کاربری.
- `first_name` (string): نام.
- `last_name` (string): نام خانوادگی.
- `profile_picture` (string, nullable): URL تصویر پروفایل.
- `score` (integer): امتیاز کاربر.
- `rank` (string, nullable): رتبه کاربر.
- `role` (string, nullable): نقش کاربر.
- `in_game_ids` (array of objects): لیست شناسه‌های کاربر در بازی‌های مختلف.

### ۲.۲. Conversation Model

- `id` (integer): شناسه یکتای گفتگو.
- `participants` (array of User): لیست کاربران شرکت‌کننده در گفتگو.
- `created_at` (datetime): زمان ایجاد گفتگو.
- `last_message` (Message object, nullable): آخرین پیام ارسال شده در این گفتگو.

### ۲.۳. Message Model

- `id` (integer): شناسه یکتای پیام.
- `conversation` (integer): شناسه گفتگوی مرتبط.
- `sender` (User object): کاربری که پیام را ارسال کرده.
- `content` (string): محتوای پیام.
- `timestamp` (datetime): زمان ارسال پیام.
- `is_read` (boolean): آیا پیام خوانده شده است.
- `is_edited` (boolean): آیا پیام ویرایش شده است.
- `is_deleted` (boolean): آیا پیام (به صورت منطقی) حذف شده است.
- `attachments` (array of Attachment): لیست فایل‌های پیوست.

### ۲.۴. Attachment Model

- `id` (integer): شناسه یکتای پیوست.
- `message` (integer): شناسه پیام مرتبط.
- `file` (string): URL فایل آپلود شده.
- `uploaded_at` (datetime): زمان آپلود فایل.

## ۳. Endpoints REST API

### ۳.۱. Conversations

#### `GET /api/conversations/`

لیست تمام گفتگوهایی که کاربر فعلی در آن‌ها شرکت دارد را برمی‌گرداند.

- **Response**: `200 OK`
  - Body:
    ```json
    [
      {
        "id": 1,
        "participants": [ ... ],
        "created_at": "2023-10-27T10:00:00Z",
        "last_message": { ... }
      }
    ]
    ```

#### `GET /api/conversations/{id}/`

اطلاعات یک گفتگوی خاص را بر اساس شناسه آن برمی‌گرداند.

- **Response**: `200 OK`
  - Body: (ساختار مشابه یک آبجکت از لیست بالا)

### ۳.۲. Messages

#### `POST /api/messages/`

یک پیام جدید ارسال می‌کند. **نکته مهم:** این endpoint هم برای ارسال پیام در یک گفتگوی موجود و هم برای **ایجاد یک گفتگوی جدید** استفاده می‌شود.

- اگر بین کاربر فعلی و `recipient_id` از قبل گفتگویی وجود داشته باشد، پیام به آن اضافه می‌شود.
- اگر گفتگویی وجود نداشته باشد، یک گفتگوی جدید بین این دو کاربر ساخته شده و پیام به عنوان اولین پیام در آن ثبت می‌شود.

- **Request Body**: `application/json`
  ```json
  {
    "content": "سلام، این یک پیام آزمایشی است.",
    "recipient_id": 2
  }
  ```
- **Response**: `201 Created`
  - Body: (ساختار کامل Message Model)

#### `GET /api/conversations/{conversation_pk}/messages/`

لیست پیام‌های یک گفتگوی خاص را برمی‌گرداند. این لیست صفحه‌بندی (Paginated) شده است.

- **Response**: `200 OK`
  - Body:
    ```json
    {
      "count": 100,
      "next": "url/to/next/page",
      "previous": "url/to/previous/page",
      "results": [
        {
          "id": 1,
          "sender": { ... },
          "content": "...",
          ...
        }
      ]
    }
    ```

#### `GET /api/messages/{id}/`
#### `PUT /api/messages/{id}/`
#### `PATCH /api/messages/{id}/`
#### `DELETE /api/messages/{id}/`

عملیات استاندارد CRUD بر روی یک پیام خاص. کاربر فقط می‌تواند پیام‌های خودش را ویرایش یا حذف کند.

### ۳.۳. Attachments

#### `POST /api/conversations/{conversation_pk}/messages/{message_pk}/attachments/`

یک فایل پیوست به یک پیام خاص اضافه می‌کند.

- **محدودیت‌های آپلود:**
  - **حداکثر حجم فایل:** ۱۰ مگابایت.
  - **فرمت‌های مجاز:** `.jpg`, `.jpeg`, `.png`, `.mp4`, `.mov`, `.webp`, `.gif`, `.heic`, `.avif`.
- **Request Body**: `multipart/form-data`
  - `file`: فایل مورد نظر برای آپلود.
- **Response**: `201 Created`
  - Body: (ساختار Attachment Model)

## ۴. مدیریت خطا (Error Handling)

API از کدهای وضعیت HTTP استاندارد برای نشان دادن موفقیت یا شکست درخواست استفاده می‌کند.

- `2xx`: موفقیت آمیز.
- `400 Bad Request`: درخواست نامعتبر بود (مثلاً فیلدهای مورد نیاز ارسال نشده).
- `401 Unauthorized`: احراز هویت انجام نشده است.
- `403 Forbidden`: شما مجوز دسترسی به این منبع را ندارید.
- `404 Not Found`: منبع مورد نظر یافت نشد.

بدنه پاسخ خطا معمولاً شامل یک پیام است:
```json
{
  "detail": "توضیحات خطا."
}
```

## ۵. ارتباطات WebSocket

برای ارتباطات لحظه‌ای (real-time) مانند ارسال و دریافت آنی پیام، از WebSocket استفاده می‌شود.

### ۵.۱. آدرس اتصال (Connection URL)

کلاینت باید به آدرس زیر متصل شود (`BASE_URL` بدون `/api`):

`ws://<BASE_URL>/ws/chat/{conversation_id}/`

یا در حالت امن:

`wss://<BASE_URL>/ws/chat/{conversation_id}/`

- **`conversation_id`**: شناسه گفتگویی که کاربر می‌خواهد به آن متصل شود.
- **احراز هویت**: اتصال WebSocket از همان session/cookie احراز هویت کاربر در ارتباطات HTTP استفاده می‌کند. بنابراین کاربر باید قبل از تلاش برای اتصال، لاگین کرده باشد.

### ۵.۲. رفتار خطا

در صورتی که کلاینت یک رویداد نامعتبر ارسال کند (مثلاً تلاش برای ویرایش پیام کاربر دیگر)، سرور هیچ پاسخی به آن کلاینت ارسال نمی‌کند و درخواست را نادیده می‌گیرد.

### ۵.۳. رویدادهای ارسالی از کلاینت به سرور (Client-to-Server Events)

کلاینت رویدادها را در قالب JSON به سرور ارسال می‌کند. هر پیام باید یک فیلد `type` داشته باشد.

#### `chat_message`
برای ارسال یک پیام متنی جدید.

- **ساختار:**
  ```json
  {
    "type": "chat_message",
    "content": "محتوای پیام جدید."
  }
  ```

#### `edit_message`
برای ویرایش یک پیام موجود. (کاربر فقط می‌تواند پیام خود را ویرایش کند)

- **ساختار:**
  ```json
  {
    "type": "edit_message",
    "message_id": 123,
    "content": "محتوای ویرایش شده."
  }
  ```

#### `delete_message`
برای حذف یک پیام موجود. (کاربر فقط می‌تواند پیام خود را حذف کند)

- **ساختار:**
  ```json
  {
    "type": "delete_message",
    "message_id": 123
  }
  ```

#### `typing`
برای اطلاع‌رسانی وضعیت "در حال تایپ".

- **ساختار:**
  ```json
  {
    "type": "typing",
    "is_typing": true
  }
  ```
  برای توقف، همین رویداد را با `is_typing: false` ارسال کنید.

### ۵.۴. رویدادهای دریافتی از سرور به کلاینت (Server-to-Client Events)

سرور رویدادها را به تمام کلاینت‌های متصل به یک گفتگو ارسال می‌کند.

#### `new_message`
یک پیام جدید در گفتگو ثبت شده است.

- **نکته مهم:** فیلد `attachments` در این رویداد وجود **ندارد**. اگر پیام حاوی پیوست باشد، کلاینت باید برای دریافت اطلاعات کامل پیوست‌ها، پیام را از طریق REST API (`GET /api/messages/{id}/`) مجدداً فراخوانی کند.

- **ساختار:**
  ```json
  {
    "type": "new_message",
    "message": {
      "id": 124,
      "sender": {
          "id": 2,
          "username": "user2",
          "profile_picture": null
      },
      "content": "محتوای پیام جدید.",
      "timestamp": "2023-10-27T14:00:00Z"
    }
  }
  ```

#### `message_edited`
یک پیام ویرایش شده است.

- **ساختار:**
  ```json
  {
    "type": "message_edited",
    "message": {
      "id": 123,
      "content": "محتوای ویرایش شده."
    }
  }
  ```

#### `message_deleted`
یک پیام حذف شده است.

- **ساختار:**
  ```json
  {
    "type": "message_deleted",
    "message_id": 123
  }
  ```

#### `user_typing`
کاربری در حال تایپ کردن است.

- **ساختار:**
  ```json
  {
    "type": "user_typing",
    "user": {
        "id": 1,
        "username": "user1",
        "profile_picture": "url/to/image.jpg"
    },
    "is_typing": true
  }
  ```

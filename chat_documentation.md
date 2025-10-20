# مستندات ماژول چت

این مستندات شامل جزئیات فنی ماژول چت، شامل عملکرد وب‌ساکت و APIهای RESTful است.

## عملکرد وب‌ساکت (WebSocket)

ارتباطات بی‌درنگ در این سیستم از طریق وب‌ساکت و با استفاده از کتابخانه `channels` جنگو مدیریت می‌شود.

### چرخه حیات اتصال (Connection Lifecycle)

1.  **اتصال (Connection):**
    *   کلاینت یک اتصال وب‌ساکت به آدرس زیر برقرار می‌کند:
        ```
        ws://<your_domain>/ws/chat/<conversation_id>/
        ```
    *   `conversation_id` شناسه‌ی یکتای مکالمه است.
    *   سرور در `consumers.py` و در متد `connect` اتصال را مدیریت می‌کند.
    *   برای برقراری اتصال، کاربر باید احراز هویت شده باشد (`user.is_authenticated`). در غیر این صورت، اتصال بسته می‌شود.
    *   پس از اتصال موفق، کاربر به یک گروه در `channel layer` با نام `chat_<conversation_id>` اضافه می‌شود تا بتواند پیام‌های مربوط به آن مکالمه را دریافت کند.

2.  **قطع اتصال (Disconnection):**
    *   هنگامی که کلاینت اتصال را قطع می‌کند، متد `disconnect` فراخوانی می‌شود.
    *   کاربر از گروه `channel layer` حذف می‌شود تا دیگر پیام‌های آن مکالمه را دریافت نکند.

### انواع پیام‌ها و جریان داده (Message Types and Data Flow)

پیام‌ها در قالب JSON بین کلاینت و سرور رد و بدل می‌شوند. هر پیام باید دارای یک کلید `type` باشد که نوع آن را مشخص می‌کند.

#### پیام‌های ارسالی از کلاینت به سرور

1.  **ارسال پیام جدید (`chat_message`):**
    *   **توضیحات:** برای ارسال یک پیام متنی جدید در مکالمه.
    *   **ساختار پیام:**
        ```json
        {
          "type": "chat_message",
          "message": "سلام، این یک پیام جدید است."
        }
        ```
    *   **عملکرد سرور:**
        *   متد `handle_chat_message` پیام را دریافت می‌کند.
        *   پیام در دیتابیس (مدل `Message`) ذخیره می‌شود.
        *   سپس پیام به تمام کلاینت‌های متصل در همان گروه (`chat_<conversation_id>`) ارسال می‌شود.

2.  **ویرایش پیام (`edit_message`):**
    *   **توضیحات:** برای ویرایش یک پیام موجود.
    *   **ساختار پیام:**
        ```json
        {
          "type": "edit_message",
          "message_id": 123,
          "content": "این محتوای ویرایش شده پیام است."
        }
        ```
    *   **عملکرد سرور:**
        *   متد `handle_edit_message` درخواست را پردازش می‌کند.
        *   سرور بررسی می‌کند که آیا فرستنده پیام همان کاربری است که درخواست ویرایش را ارسال کرده است یا خیر.
        *   محتوای پیام در دیتابیس به‌روزرسانی شده و فیلد `is_edited` به `True` تغییر می‌کند.
        *   یک پیام `message.edited` برای اطلاع‌رسانی به سایر کلاینت‌ها ارسال می‌شود.

3.  **حذف پیام (`delete_message`):**
    *   **توضیحات:** برای حذف یک پیام. پیام به صورت نرم حذف می‌شود (soft delete).
    *   **ساختار پیام:**
        ```json
        {
          "type": "delete_message",
          "message_id": 123
        }
        ```
    *   **عملکرد سرور:**
        *   متد `handle_delete_message` درخواست را پردازش می‌کند.
        *   سرور بررسی می‌کند که آیا فرستنده پیام همان کاربری است که درخواست حذف را ارسال کرده است یا خیر.
        *   فیلد `is_deleted` پیام در دیتابیس به `True` تغییر می‌کند.
        *   یک پیام `message.deleted` برای اطلاع‌رسانی به سایر کلاینت‌ها ارسال می‌شود.

4.  **اعلان در حال تایپ (`typing`):**
    *   **توضیحات:** برای اطلاع‌رسانی به دیگران مبنی بر اینکه کاربر در حال تایپ کردن است.
    *   **ساختار پیام:**
        ```json
        {
          "type": "typing",
          "is_typing": true
        }
        ```
    *   **عملکرد سرور:**
        *   متد `handle_typing` این رویداد را دریافت کرده و یک پیام `user.typing` به سایر کلاینت‌های گروه ارسال می‌کند. این پیام در دیتابیس ذخیره نمی‌شود.

#### پیام‌های ارسالی از سرور به کلاینت

1.  **پیام چت جدید (`chat.message`):**
    *   **ساختار پیام:**
        ```json
        {
          "id": 456,
          "sender": "username",
          "content": "سلام، این یک پیام جدید است.",
          "timestamp": "2023-10-27T10:00:00Z"
        }
        ```

2.  **پیام ویرایش شده (`message.edited`):**
    *   **ساختار پیام:**
        ```json
        {
          "type": "message.edited",
          "message": {
            "id": 123,
            "content": "این محتوای ویرایش شده پیام است."
          }
        }
        ```

3.  **پیام حذف شده (`message.deleted`):**
    *   **ساختار پیام:**
        ```json
        {
          "type": "message.deleted",
          "message_id": 123
        }
        ```

4.  **کاربر در حال تایپ (`user.typing`):**
    *   **ساختار پیام:**
        ```json
        {
          "type": "user.typing",
          "user": "username",
          "is_typing": true
        }
        ```

## APIهای RESTful

APIهای زیر برای مدیریت مکالمات، پیام‌ها و فایل‌های پیوست در دسترس هستند.

### احراز هویت (Authentication)

تمام APIها نیازمند احراز هویت هستند. کاربر باید توکن خود را در هدر `Authorization` ارسال کند.

### مدیریت مکالمات (Conversations)

*   **Endpoint:** `/api/conversations/`
*   **ViewSet:** `ConversationViewSet`

#### `GET /api/conversations/`

*   **توضیحات:** دریافت لیست تمام مکالماتی که کاربر در آن‌ها شرکت دارد.
*   **پاسخ موفقیت‌آمیز (200 OK):**
    ```json
    [
      {
        "id": 1,
        "participants": [
          { "id": 1, "username": "user1" },
          { "id": 2, "username": "user2" }
        ],
        "created_at": "2023-10-27T10:00:00Z",
        "last_message": {
          "id": 123,
          "sender": { "id": 1, "username": "user1" },
          "content": "آخرین پیام",
          "timestamp": "2023-10-27T11:00:00Z",
          "is_read": false
        },
        "support_ticket": null
      }
    ]
    ```

#### `POST /api/conversations/`

*   **توضیحات:** ایجاد یک مکالمه جدید.
*   **بدنه درخواست (Request Body):**
    ```json
    {
      "participants": [2, 3]
    }
    ```
    *   `participants`: لیستی از IDهای کاربرانی که باید در مکالمه باشند.
*   **پاسخ موفقیت‌آمیز (201 Created):**
    *   بدنه پاسخ شامل اطلاعات مکالمه جدید است.

### مدیریت پیام‌ها (Messages)

*   **Endpoint:** `/api/conversations/<conversation_pk>/messages/`
*   **ViewSet:** `MessageViewSet`

#### `GET /api/conversations/<conversation_pk>/messages/`

*   **توضیحات:** دریافت لیست تمام پیام‌های یک مکالمه.
*   **پاسخ موفقیت‌آمیز (200 OK):**
    ```json
    [
      {
        "id": 1,
        "sender": { "id": 1, "username": "user1" },
        "content": "سلام",
        "timestamp": "2023-10-27T10:00:00Z",
        "is_read": true,
        "is_edited": false,
        "is_deleted": false
      }
    ]
    ```

#### `POST /api/conversations/<conversation_pk>/messages/`

*   **توضیحات:** ارسال یک پیام جدید در مکالمه.
*   **بدنه درخواست (Request Body):**
    ```json
    {
      "content": "این یک پیام جدید است."
    }
    ```
*   **پاسخ موفقیت‌آمیز (201 Created):**
    *   بدنه پاسخ شامل اطلاعات پیام جدید است.

### مدیریت فایل‌های پیوست (Attachments)

*   **Endpoint:** `/api/conversations/<conversation_pk>/messages/<message_pk>/attachments/`
*   **ViewSet:** `AttachmentViewSet`

#### `POST /api/conversations/<conversation_pk>/messages/<message_pk>/attachments/`

*   **توضیحات:** افزودن یک فایل پیوست به یک پیام.
*   **بدنه درخواست (Request Body):**
    *   این یک درخواست `multipart/form-data` است و باید شامل فایل باشد.
    *   فیلد `file`: فایل مورد نظر.
*   **پاسخ موفقیت‌آمیز (201 Created):**
    *   بدنه پاسخ شامل اطلاعات فایل پیوست جدید است.

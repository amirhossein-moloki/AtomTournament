# مستندات چت API

این مستندات به شما کمک می‌کند تا از سیستم چت این پروژه استفاده کنید. سیستم چت از دو بخش اصلی تشکیل شده است:

1.  **Chat REST API**: برای مدیریت مکالمات، پیام‌ها و فایل‌های پیوست.
2.  **Chat WebSocket API**: برای ارتباطات real-time مانند ارسال و دریافت آنی پیام‌ها.

---

## Chat REST API

برای تعامل با API، باید توکن احراز هویت خود را در هدر `Authorization` به‌صورت `Bearer <your-auth-token>` ارسال کنید.

### مدیریت مکالمات (Conversations)

#### `GET /api/conversations/`

لیست تمام مکالماتی که کاربر در آن‌ها عضو است را برمی‌گرداند.

- **متد:** `GET`
- **نیازمند احراز هویت:** بله
- **پاسخ:** لیستی از آبجکت‌های مکالمه.

**پاسخ نمونه:**

```json
[
  {
    "id": 1,
    "participants": ["user1", "user2"],
    "created_at": "2024-01-01T12:00:00Z"
  }
]
```

#### `POST /api/conversations/`

یک مکالمه جدید ایجاد می‌کند.

- **متد:** `POST`
- **نیازمند احراز هویت:** بله
- **پارامترها:**
  - `participants`: لیستی از شناسه‌های کاربری برای افزودن به مکالمه.

**بدنه درخواست نمونه:**

```json
{
  "participants": [2, 3]
}
```

---

### مدیریت پیام‌ها (Messages)

#### `GET /api/conversations/{conversation_id}/messages/`

لیست تمام پیام‌های یک مکالمه را برمی‌گرداند.

- **متد:** `GET`
- **نیازمند احراز هویت:** بله
- **پاسخ:** لیستی از آبجکت‌های پیام.

**پاسخ نمونه:**

```json
[
  {
    "id": 1,
    "sender": "user1",
    "content": "سلام!",
    "timestamp": "2024-01-01T12:01:00Z",
    "is_edited": false,
    "is_deleted": false,
    "attachments": []
  }
]
```

#### `POST /api/conversations/{conversation_id}/messages/`

یک پیام جدید در یک مکالمه ایجاد می‌کند.

- **متد:** `POST`
- **نیازمند احراز هویت:** بله
- **پارامترها:**
  - `content`: محتوای پیام.

**بدنه درخواست نمونه:**

```json
{
  "content": "این یک پیام جدید است."
}
```

---

### مدیریت پیوست‌ها (Attachments)

#### `GET /api/conversations/{conversation_id}/messages/{message_id}/attachments/`

لیست تمام پیوست‌های یک پیام را برمی‌گرداند.

- **متد:** `GET`
- **نیازمند احراز هویت:** بله
- **پاسخ:** لیستی از آبجکت‌های پیوست.

#### `POST /api/conversations/{conversation_id}/messages/{message_id}/attachments/`

یک فایل پیوست به یک پیام اضافه می‌کند.

- **متد:** `POST`
- **نیازمند احراز هویت:** بله
- **نوع محتوا:** `multipart/form-data`
- **پارامترها:**
  - `file`: فایل مورد نظر برای آپلود.

**پاسخ نمونه برای هر دو متد:**

```json
{
  "id": 1,
  "file": "http://<your-domain>/media/attachments/file.jpg",
  "uploaded_at": "2024-01-01T12:02:00Z"
}
```

---

## Chat WebSocket API

برای اتصال به وب‌ساکت، از آدرس `ws://<your-domain>/ws/chat/{conversation_id}/` استفاده کنید.

### احراز هویت

برای اتصال به وب‌ساکت، کاربر باید احراز هویت شده باشد. کلاینت باید توکن احراز هویت را همراه با درخواست اتصال ارسال کند. این کار معمولاً از طریق هدر `Authorization` یا کوئری پارامتر انجام می‌شود.

**مثال با کوئری پارامتر:**

`ws://<your-domain>/ws/chat/{conversation_id}/?token=<your-auth-token>`

**مثال با هدر (در جاوااسکریپت):**

```javascript
const socket = new WebSocket('ws://<your-domain>/ws/chat/1/', [], {
  headers: {
    Authorization: 'Bearer <your-auth-token>'
  }
});
```

### ارسال پیام

برای ارسال پیام، یک آبجکت JSON با ساختار زیر به وب‌ساکت ارسال کنید:

```json
{
  "type": "chat_message",
  "message": "محتوای پیام شما"
}
```

### ویرایش پیام

```json
{
  "type": "edit_message",
  "message_id": 123,
  "content": "محتوای جدید پیام"
}
```

### حذف پیام

```json
{
  "type": "delete_message",
  "message_id": 123
}
```

### Typing Indicator

برای اطلاع‌رسانی به دیگران که در حال تایپ هستید:

```json
{
  "type": "typing",
  "is_typing": true
}
```

### دریافت رویدادها (Events)

#### پیام جدید

```json
{
  "type": "chat.message",
  "message": {
    "id": 123,
    "sender": "username",
    "content": "محتوای پیام",
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

#### پیام ویرایش شده

```json
{
  "type": "message.edited",
  "message": {
    "id": 123,
    "content": "محتوای جدید پیام"
  }
}
```

#### پیام حذف شده

```json
{
  "type": "message.deleted",
  "message_id": 123
}
```

#### Typing Indicator

```json
{
  "type": "user.typing",
  "user": "username",
  "is_typing": true
}
```

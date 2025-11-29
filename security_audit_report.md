# گزارش جامع بررسی امنیت بک‌اند

**تاریخ گزارش:** ۲۹ نوامبر ۲۰۲۵
**متخصص امنیت:** Jules (هوش مصنوعی امنیتی)

---

## ۱. خلاصه مدیریتی

این گزارش نتایج یک بررسی امنیتی جامع بر روی پروژه Django Tournament Management System را ارائه می‌دهد. در طول این بررسی، چندین آسیب‌پذیری شناسایی شد که نیازمند توجه فوری هستند.

**مهم‌ترین یافته‌ها:**

1.  **آسیب‌پذیری بحرانی در سیستم کیف پول:** یک نقص بزرگ در بخش مدیریت درخواست‌های برداشت وجه شناسایی شد که به هر کاربر احرازهویت‌شده اجازه می‌دهد تا هر درخواست برداشتی را تأیید یا رد کند.
2.  **آسیب‌پذیری بحرانی در منطق مسابقات:** یک نقص حیاتی در سرویس تأیید نتایج مسابقات وجود دارد که به هر کاربر احرازهویت‌شده اجازه می‌دهد نتیجه هر مسابقه‌ای را در سیستم تعیین کند.
3.  **نشت گسترده اطلاعات:** بسیاری از نقاط پایانی (Endpoints) اصلی پروژه، لیست کاملی از کاربران، تیم‌ها و مسابقات را به صورت عمومی و بدون نیاز به احرازهویت نمایش می‌دهند.
4.  **پیکربندی‌های امنیتی ضعیف:** چندین مورد از تنظیمات پروژه، از جمله CORS و محدودیت نرخ درخواست (Rate Limiting)، می‌توانند برای افزایش امنیت بهینه‌سازی شوند.

در مجموع، معماری کلی پروژه از الگوهای امنیتی خوبی مانند لایه سرویس و کلاس‌های دسترسی سفارشی استفاده می‌کند، اما چندین اشتباه پیاده‌سازی، امنیت سیستم را به شدت تضعیف کرده‌اند. توصیه می‌شود آسیب‌پذیری‌های **بحرانی** و **بالا** در اسرع وقت برطرف شوند.

---

## ۲. جزئیات آسیب‌پذیری‌ها

### ۲.۱. آسیب‌پذیری‌های بحرانی (Critical)

#### ۲.۱.۱. کنترل دسترسی شکسته در تأیید و رد درخواست‌های برداشت وجه

-   **شدت:** **بحرانی**
-   **مکان:** `wallet/views.py` - کلاس `AdminWithdrawalRequestViewSet`
-   **توضیحات:** این ViewSet که برای مدیریت درخواست‌های برداشت وجه طراحی شده، از `permission_classes = [IsAuthenticated]` استفاده می‌کند. این بدان معناست که **هر کاربر احرازهویت‌شده‌ای**، صرف نظر از سطح دسترسی، می‌تواند به این نقطه پایانی دسترسی پیدا کرده، لیست تمام درخواست‌های برداشت را مشاهده کند و آن‌ها را تأیید یا رد نماید. این آسیب‌پذیری می‌تواند منجر به سرقت مستقیم وجوه از طریق تأیید درخواست‌های برداشت جعلی یا رد کردن درخواست‌های قانونی شود.
-   **اصلاحیه پیشنهادی:**
    کلاس دسترسی را به `IsAdminUser` تغییر دهید تا اطمینان حاصل شود که فقط مدیران سیستم می‌توانند به این قابلیت دسترسی داشته باشند.

    ```python
    # In wallet/views.py

    from rest_framework.permissions import IsAdminUser, IsAuthenticated

    class AdminWithdrawalRequestViewSet(viewsets.ModelViewSet):
        queryset = WithdrawalRequest.objects.all()
        serializer_class = WithdrawalRequestSerializer
        permission_classes = [IsAdminUser]  # FIX: Should be IsAdminUser

        # ... rest of the view
    ```

#### ۲.۱.۲. امکان دستکاری نتایج مسابقات توسط هر کاربر (IDOR)

-   **شدت:** **بحرانی**
-   **مکان:** `tournaments/views.py` (کلاس `MatchViewSet`) و `tournaments/services.py` (تابع `confirm_match_result`)
-   **توضیحات:** اکشن `confirm_result` در `MatchViewSet` تنها به `IsAuthenticated` نیاز دارد. منطق اصلی در سرویس `confirm_match_result` هیچ‌گونه بررسی برای اطمینان از اینکه کاربر درخواست‌دهنده یکی از شرکت‌کنندگان مسابقه است، انجام نمی‌دهد. در نتیجه، **هر کاربر احرازهویت‌شده‌ای** می‌تواند برای هر مسابقه‌ای در سیستم، هر تیم یا بازیکنی را به عنوان برنده اعلام کند. این آسیب‌پذیری یکپارچگی کل سیستم مسابقات را از بین می‌برد.
-   **اصلاحیه پیشنهادی:**
    قبل از تأیید نتیجه، بررسی کنید که کاربر درخواست‌دهنده یکی از شرکت‌کنندگان آن مسابقه باشد.

    ```python
    # In tournaments/views.py

    from rest_framework.exceptions import PermissionDenied

    class MatchViewSet(viewsets.ModelViewSet):
        # ...

        @action(detail=True, methods=["post"])
        def confirm_result(self, request, pk=None):
            match = self.get_object()

            # FIX: Add authorization check
            if not match.is_participant(request.user):
                raise PermissionDenied("You are not a participant in this match.")

            winner_id = request.data.get("winner_id")
            # ... rest of the function
    ```
    همچنین، مدل `Match` باید یک متد `is_participant` داشته باشد:
    ```python
    # In tournaments/models.py

    class Match(models.Model):
        # ...
        def is_participant(self, user):
            if self.match_type == 'individual':
                return user in [self.participant1_user, self.participant2_user]
            else: # team
                return self.participant1_team.members.filter(id=user.id).exists() or \
                       self.participant2_team.members.filter(id=user.id).exists()
    ```

### ۲.۲. آسیب‌پذیری‌های با شدت بالا (High)

#### ۲.۲.۱. نشت اطلاعات از طریق لیست‌های عمومی کاربران و تیم‌ها

-   **شدت:** **بالا**
-   **مکان:**
    -   `users/views.py` - `UserViewSet`
    -   `teams/views.py` - `TeamViewSet`
    -   `tournaments/views.py` - `TournamentViewSet`, `MatchViewSet`, `GameViewSet`
-   **توضیحات:** چندین ViewSet در پروژه، متد `get_permissions` خود را طوری بازنویسی کرده‌اند که برای اکشن‌های `list` و `retrieve` از `[AllowAny()]` استفاده کنند. این باعث می‌شود نقاط پایانی `/api/users/`, `/api/teams/` و `/api/tournaments/` به صورت عمومی قابل دسترس باشند و لیست کاملی از تمام داده‌ها را به هر کاربر غیر احرازهویت‌شده‌ای نمایش دهند. این یک نشت اطلاعات قابل توجه است که می‌تواند برای شناسایی کاربران و ساختار تیم‌ها مورد سوءاستفاده قرار گیرد.
-   **اصلاحیه پیشنهادی:**
    مقدار پیش‌فرض کلاس‌های دسترسی را به `IsAuthenticated` یا `IsAuthenticatedOrReadOnly` تغییر دهید و منطق `get_permissions` را حذف یا اصلاح کنید. برای لیست‌های عمومی، از یک Serializer جداگانه استفاده کنید که فقط اطلاعات غیرحساس را نمایش دهد.

    ```python
    # In users/views.py and teams/views.py

    class UserViewSet(viewsets.ModelViewSet):
        # ...
        permission_classes = [IsAuthenticated] # FIX: Change default permission

        def get_permissions(self):
            # FIX: Remove this method or change the logic
            if self.action in ["send_otp", "verify_otp"]: # Only specific actions should be public
                return [AllowAny()]
            return super().get_permissions()

    # Apply similar changes to TeamViewSet, TournamentViewSet, etc.
    ```

### ۲.۳. آسیب‌پذیری‌های با شدت متوسط (Medium)

#### ۲.۳.۱. عدم وجود اعتبارسنجی کافی در Serializerها

-   **شدت:** **متوسط**
-   **مکان:**
    -   `wallet/serializers.py` - `CreateWithdrawalRequestSerializer`
    -   `users/serializers.py` - `UserSerializer`
    -   `tournaments/serializers.py` - `TournamentCreateUpdateSerializer`
-   **توضیحات:**
    1.  **شماره کارت و شبا:** در `CreateWithdrawalRequestSerializer`، فیلدهای `card_number` و `sheba_number` هیچ‌گونه اعتبارسنجی فرمت ندارند و داده‌های نامعتبر می‌توانند در پایگاه داده ذخیره شوند.
    2.  **بروزرسانی تودرتو (Nested Update):** در `UserSerializer`، متد `update` داده‌های `in_game_ids` را بدون استفاده از یک Serializer اعتبارسنجی می‌کند. این می‌تواند منجر به خطاهای سرور (500) در صورت ارسال داده‌های ناقص یا اشتباه شود.
    3.  **استفاده از `__all__`:** چندین Serializer مانند `TournamentColorSerializer` از `fields = "__all__"` استفاده می‌کنند که یک رویه ضعیف است و می‌تواند در آینده منجر به نشت ناخواسته اطلاعات شود.
-   **اصلاحیه پیشنهادی:**
    1.  برای شماره کارت و شبا، از اعتبارسنجی با Regex یا کتابخانه‌های معتبر استفاده کنید.
    2.  در متد `update` مربوط به `UserSerializer`، از `InGameIDSerializer(many=True)` برای اعتبارسنجی داده‌های ورودی استفاده کنید.
    3.  تمام موارد استفاده از `__all__` را با لیست صریح فیلدها جایگزین کنید.

#### ۲.۳.۲. پیکربندی ضعیف CORS

-   **شدت:** **متوسط**
-   **مکان:** `tournament_project/settings.py`
-   **توضیحات:** تنظیمات `CORS_ALLOW_ALL_ORIGINS` از یک متغیر محیطی خوانده می‌شود. اگر این متغیر به اشتباه روی `True` تنظیم شود، هر وب‌سایتی می‌تواند به API شما درخواست ارسال کند که یک خطر امنیتی بزرگ است.
-   **اصلاحیه پیشنهادی:**
    یک سیاست سخت‌گیرانه‌تر اعمال کنید. `CORS_ALLOW_ALL_ORIGINS` را همیشه روی `False` تنظیم کرده و فقط دامنه‌های مشخصی را در `CORS_ALLOWED_ORIGINS` (یا `CORS_TRUSTED_ORIGINS`) قرار دهید.

#### ۲.۳.۳. Rate Limiting غیردقیق

-   **شدت:** **متوسط**
-   **مکان:** `tournament_project/settings.py`
-   **توضیحات:** محدودیت نرخ درخواست به صورت کلی برای تمام APIها تنظیم شده است. نقاط حساس مانند `send_otp` یا لاگین باید محدودیت‌های بسیار سخت‌گیرانه‌تری (مثلاً ۱ درخواست در دقیقه) داشته باشند تا از حملات brute-force یا اسپم جلوگیری شود.
-   **اصلاحیه پیشنهادی:**
    از throttling مبتنی بر view در DRF استفاده کنید تا برای نقاط پایانی حساس، محدودیت‌های دقیق‌تر و کوتاه‌مدت‌تری اعمال کنید.

---

## ۳. چک‌لیست افزایش امنیت (Hardening)

-   [ ] **بررسی تمام ViewSetها:** اطمینان حاصل کنید که هیچ ViewSet دیگری از الگوی `AllowAny` برای لیست کردن داده‌های حساس استفاده نمی‌کند.
-   [ ] **استفاده از `Enum` برای وضعیت‌ها:** در مدل‌ها، برای فیلدهای وضعیت (مانند `status` در `WithdrawalRequest`) از `models.TextChoices` یا `Enum` استفاده کنید تا از ورود مقادیر نامعتبر در سطح پایگاه داده جلوگیری شود.
-   [ ] **فعال‌سازی `SECURE_SSL_REDIRECT`:** در محیط پروداکشن، اطمینان حاصل کنید که `SECURE_SSL_REDIRECT` همیشه `True` است تا تمام ترافیک به HTTPS منتقل شود.
-   [ ] **تنظیمات کوکی‌های امن:** `SESSION_COOKIE_SECURE` و `CSRF_COOKIE_SECURE` را در محیط پروداکشن روی `True` تنظیم کنید.
-   [ ] **افزودن `whitenoise`:** برای ارائه امن و بهینه فایل‌های استاتیک در پروداکشن، از `whitenoise` استفاده کنید.
-   [ ] **بررسی وابستگی‌ها (Dependencies):** به طور منظم با ابزارهایی مانند `pip-audit` یا `safety`، وابستگی‌های پروژه را برای آسیب‌پذیری‌های شناخته‌شده اسکن کنید.

---

## ۴. نتیجه‌گیری

پروژه از نظر معماری پایه‌های خوبی دارد، اما چندین آسیب‌پذیری بحرانی و با شدت بالا در پیاده‌سازی آن وجود دارد که امنیت کاربران و یکپارچگی داده‌ها را به خطر می‌اندازد. توصیه اکید می‌شود که تیم توسعه در اسرع وقت برای رفع موارد ذکرشده در این گزارش، به خصوص آسیب‌پذیری‌های مربوط به کیف پول و نتایج مسابقات، اقدام نماید.

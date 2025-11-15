# وظایف تخصصی توسعه‌دهنده بک‌اند برای پیاده‌سازی استراتژی سئو

این سند وظایف مشخصی را که یک توسعه‌دهنده بک‌اند باید برای اجرای موفقیت‌آمیز راهکارهای پیشنهادی در گزارش سئو انجام دهد، تشریح می‌کند.

---

## ۱. توسعه سرویس تزریق لینک خودکار (Auto-Linking Service)

**هدف:** ایجاد یک مکانیزم هوشمند برای تبدیل کلمات کلیدی (مانند نام بازی‌ها و تورنمنت‌ها) در محتوای پست‌های وبلاگ به لینک‌های داخلی.

**وظایف مشخص:**

1.  **ایجاد یک تابع یا سرویس جدید:**
    - یک فایل جدید در `blog/services.py` یا `blog/utils.py` ایجاد کنید.
    - یک تابع به نام `inject_internal_links(content)` تعریف کنید که یک رشته (محتوای پست) را به عنوان ورودی می‌گیرد.

2.  **دریافت لیست کلمات کلیدی:**
    - این تابع باید به دیتابیس متصل شده و لیستی از نام تمام بازی‌ها (`Game.objects.all()`) و تورنمنت‌های فعال (`Tournament.objects.filter(status='active')`) را دریافت کند.

3.  **جستجو و جایگزینی:**
    - تابع باید در `content` ورودی، به دنبال نام بازی‌ها و تورنمنت‌ها بگردد.
    - برای هر کلمه‌ای که پیدا می‌شود، یک تگ `<a>` HTML با `href` مناسب جایگزین آن کند.
        - **مثال:** اگر کلمه "FIFA 24" پیدا شد، باید به `<a href="/tournaments?game=fifa-24">FIFA 24</a>` تبدیل شود. (توجه: آدرس URL نهایی باید با ساختار فرانت‌اند هماهنگ باشد).
    - **بهینه‌سازی:** برای جلوگیری از کندی، لیست کلمات کلیدی را می‌توان کش (Cache) کرد.

4.  **ادغام با سریالایزر پست:**
    - در `blog/serializers.py`، سریالایزر `PostDetailSerializer` را ویرایش کنید.
    - یک فیلد جدید از نوع `SerializerMethodField` به نام `linked_content` اضافه کنید.
    - متد `get_linked_content` را پیاده‌سازی کنید که تابع `inject_internal_links` را روی `post.content` فراخوانی کرده و نتیجه را برمی‌گرداند.

    ```python
    # In blog/serializers.py

    from .services import inject_internal_links

    class PostDetailSerializer(serializers.ModelSerializer):
        linked_content = serializers.SerializerMethodField()

        class Meta:
            model = Post
            fields = [..., 'content', 'linked_content'] # '...' represents other fields

        def get_linked_content(self, obj):
            return inject_internal_links(obj.content)
    ```

---

## ۲. ایجاد اندپوینت برای "پست‌های مرتبط" در تورنمنت‌ها

**هدف:** فراهم کردن یک API که فرانت‌اند بتواند از آن برای نمایش لیست مقالات مرتبط در صفحه جزئیات یک تورنمنت استفاده کند.

**وظایف مشخص:**

1.  **ویرایش `TournamentViewSet`:**
    - فایل `tournaments/views.py` را باز کنید.
    - یک اکشن (action) جدید به نام `related_posts` به `TournamentViewSet` اضافه کنید، همانطور که در گزارش اصلی پیشنهاد شد.

2.  **پیاده‌سازی منطق فیلترینگ:**
    - این اکشن باید `pk` تورنمنت را دریافت کند.
    - نام بازی مربوط به آن تورنمنت (`tournament.game.name`) را استخراج کند.
    - در مدل `Post`، پست‌هایی را که در عنوان یا محتوایشان به نام آن بازی اشاره شده است، فیلتر کند (`Post.objects.filter(Q(title__icontains=game_name) | Q(content__icontains=game_name), status='published')`).
    - حداکثر ۵ پست را برگرداند.

3.  **استفاده از سریالایزر مناسب:**
    - برای سریالایز کردن پست‌های یافت‌شده، از `PostListSerializer` (که سبک‌تر است) استفاده کنید.

---

## ۳. تکمیل APIهای پروفایل تیم و کاربر

**هدف:** اطمینان از اینکه APIهای مربوط به پروفایل تیم و کاربر، داده‌های لازم برای لینک‌دهی به تاریخچه مسابقات و تورنمنت‌های شرکت‌کرده را فراهم می‌کنند.

**وظایف مشخص:**

1.  **بررسی سریالایزرهای `TeamSerializer` و `UserSerializer`:**
    - در `teams/serializers.py` و `users/serializers.py`، اطمینان حاصل کنید که این سریالایزرها یک فیلد برای لیست تورنمنت‌هایی که در آن شرکت کرده‌اند، دارند.
    - اگر این فیلد وجود ندارد، آن را با استفاده از `SerializerMethodField` یا یک رابطه `ManyToManyField` اضافه کنید.

2.  **ایجاد لینک به تاریخچه مسابقات:**
    - سریالایزرهای `TeamSerializer` و `UserSerializer` باید یک فیلد `match_history_url` داشته باشند که آدرس API مربوط به تاریخچه مسابقات (`/api/teams/{id}/match-history/`) را برمی‌گرداند. این کار را می‌توان با `HyperlinkedIdentityField` یا `SerializerMethodField` انجام داد.

    ```python
    # In teams/serializers.py

    class TeamSerializer(serializers.ModelSerializer):
        match_history_url = serializers.HyperlinkedIdentityField(
            view_name='team-match-history',
            lookup_field='pk'
        )

        class Meta:
            model = Team
            fields = [..., 'match_history_url']
    ```

---

## ۴. اطمینان از لینک‌دهی در APIهای "برترین‌ها"

**هدف:** تبدیل نام تیم‌ها و بازیکنان در صفحات `TopPlayersView` و `TopTeamsView` به لینک‌های قابل کلیک در سمت فرانت‌اند.

**وظایف مشخص:**

1.  **ویرایش سریالایزرهای مربوطه:**
    - در `teams/serializers.py`، سریالایزر `TopTeamSerializer` (و اگر وجود ندارد، `TeamSerializer`) باید شامل یک فیلد `url` باشد که به صفحه جزئیات آن تیم اشاره می‌کند.
    - مشابه همین کار باید برای سریالایزر مربوط به `TopPlayersView` در `users/serializers.py` انجام شود.
    - استفاده از `HyperlinkedModelSerializer` یا افزودن یک فیلد `url` با `HyperlinkedIdentityField` راهکار مناسبی است.

این وظایف، زیرساخت لازم در بک‌اند را برای پیاده‌سازی یک استراتژی لینک‌دهی داخلی قدرتمند فراهم می‌کنند و به تیم فرانت‌اند اجازه می‌دهند تا این داده‌ها را به شکل لینک‌های معنادار و کاربردی به کاربران نمایش دهند.

# راهنمای جامع پشتیبان‌گیری و بازیابی (PostgreSQL + Files)

این سند یک راهنمای عملیاتی کامل برای راه‌اندازی و مدیریت سیستم پشتیبان‌گیری دوگانه است:
1.  **پشتیبان‌گیری از دیتابیس PostgreSQL:** با استفاده از **WAL-G** برای پیاده‌سازی Point-in-Time Recovery (PITR).
2.  **پشتیبان‌گیری از فایل‌ها (Media/Assets):** با استفاده از **Restic** برای بکاپ‌های افزایشی و رمزنگاری‌شده.

هر دو سیستم از **Google Cloud Storage (GCS)** به عنوان مقصد ذخیره‌سازی استفاده می‌کنند.

## فهرست مطالب
1.  [پیش‌نیازها](#۱-پیش‌نیازها)
2.  [نصب خودکار](#۲-نصب-خودکار)
3.  [مراحل پس از نصب (بسیار مهم)](#۳-مراحل-پس-از-نصب-بسیار-مهم)
4.  [تست و تأیید اولیه](#۴-تست-و-تأیید-اولیه)
5.  [راهنمای بازیابی (Disaster Recovery)](#۵-راهنمای-بازیابی-disaster-recovery)
    - [بازیابی دیتابیس PostgreSQL](#بازیابی-دیتابیس-postgresql)
    - [بازیابی فایل‌ها (Restic)](#بازیابی-فایل‌ها-restic)
6.  [جزئیات فنی](#۶-جزئیات-فنی)

---

## ۱. پیش‌نیازها

- **یک VM در GCP:** با سیستم‌عامل **Ubuntu 22.04 LTS** و **PostgreSQL 14** نصب شده.
- **یک GCS Bucket:** برای ذخیره‌سازی بکاپ‌ها.
- **یک Service Account در GCP:** با نقش **"Storage Object Admin"** روی Bucket فوق و کلید JSON دانلود شده.
- **لیست مسیرهای فایل برای بکاپ:** مسیرهای دقیقی که حاوی فایل‌های مدیا و assets شما هستند (مثلاً `/var/www/media`).

---

## ۲. نصب خودکار

یک بسته نصب خودکار در دایرکتوری `deployment/` تمام مراحل نصب نرم‌افزارها و سرویس‌ها را انجام می‌دهد.

1.  **انتقال بسته به سرور:** محتویات پوشه `deployment/` را به سرور خود منتقل کنید.
    ```bash
    scp -r deployment/ user@your-server-ip:/home/user/
    ```
2.  **اجرای اسکریپت نصب:**
    ```bash
    cd /home/user/deployment
    sudo ./install.sh
    ```
    این اسکریپت WAL-G، Restic و تمام سرویس‌های `systemd` مورد نیاز را نصب و فعال می‌کند.

---

## ۳. مراحل پس از نصب (بسیار مهم)

پس از اجرای اسکریپت، مراحل کانفیگ زیر **باید به صورت دستی** انجام شوند:

### بخش PostgreSQL (WAL-G)

1.  **قرار دادن کلید GCP:**
    - کلید JSON خود را در مسیر `/etc/wal-g/gcs-key.json` قرار دهید.
    - دسترسی‌ها را تنظیم کنید:
      ```bash
      sudo mv /path/to/your-key.json /etc/wal-g/gcs-key.json
      sudo chown postgres:postgres /etc/wal-g/gcs-key.json
      sudo chmod 600 /etc/wal-g/gcs-key.json
      ```

2.  **تنظیم کانفیگ WAL-G:**
    - فایل الگو را کپی کرده و اطلاعات GCS Bucket خود را در آن وارد کنید.
      ```bash
      sudo cp deployment/walg-base-config.env.template /etc/wal-g/walg-base-config.env
      sudo nano /etc/wal-g/walg-base-config.env
      sudo chown postgres:postgres /etc/wal-g/walg-base-config.env && sudo chmod 600 /etc/wal-g/walg-base-config.env
      ```
3.  **تنظیمات PostgreSQL:**
    - فایل `postgresql.conf` را طبق راهنمای `deployment/postgres_config_guide.txt` ویرایش کنید.
4.  **ری‌استارت PostgreSQL:**
    ```bash
    sudo systemctl restart postgresql
    ```

### بخش فایل‌ها (Restic)

5.  **تنظیم کانفیگ Restic:**
    - فایل الگو را کپی کرده و آن را با اطلاعات صحیح پر کنید.
      ```bash
      sudo cp deployment/restic-env.template /etc/restic/restic-env
      sudo nano /etc/restic/restic-env
      sudo chmod 600 /etc/restic/restic-env
      ```
      **نکات مهم در این فایل:**
      - `GOOGLE_APPLICATION_CREDENTIALS` باید به همان کلید GCP در مسیر `/etc/wal-g/gcs-key.json` اشاره کند.
      - `RESTIC_REPOSITORY` را با نام GCS Bucket خود و یک مسیر مجزا برای بکاپ فایل‌ها (مانند `/restic-repo`) پر کنید.
      - `RESTIC_PASSWORD` را با یک رمز عبور بسیار قوی و جدید جایگزین کنید. **این رمز را در جای امنی نگهداری کنید!**

6.  **تعیین مسیرهای بکاپ:**
    - یک فایل جدید در مسیر `/etc/restic/paths-to-backup.txt` ایجاد کرده و لیست کامل مسیرهایی که می‌خواهید از آنها بکاپ گرفته شود را در آن وارد کنید (هر مسیر در یک خط).
      ```bash
      sudo nano /etc/restic/paths-to-backup.txt
      ```
      مثال:
      ```
      /var/www/media
      /var/www/static
      ```

7.  **راه‌اندازی اولیه مخزن Restic (فقط یک بار):**
    - این دستور مخزن رمزنگاری‌شده را در GCS Bucket شما ایجاد می‌کند.
      ```bash
      sudo bash -c ". /etc/restic/restic-env && restic init"
      ```

---

## ۴. تست و تأیید اولیه

اجرای اولین بکاپ به صورت دستی برای اطمینان از صحت عملکرد سیستم **ضروری** است.

- **تست بکاپ PostgreSQL:**
  ```bash
  sudo -u postgres bash -c ". /etc/wal-g/walg-base-config.env && wal-g backup-push /var/lib/postgresql/14/main"
  sudo -u postgres bash -c ". /etc/wal-g/walg-base-config.env && wal-g backup-list"
  ```
- **تست بکاپ فایل‌ها:**
  ```bash
  sudo bash -c ". /etc/restic/restic-env && restic backup --files-from /etc/restic/paths-to-backup.txt"
  sudo bash -c ". /etc/restic/restic-env && restic snapshots"
  ```

---

## ۵. راهنمای بازیابی (Disaster Recovery)

### بازیابی دیتابیس PostgreSQL

1.  **آماده‌سازی سرور جدید:** PostgreSQL و ابزارها را با اسکریپت `install.sh` نصب کنید. فایل‌های کانفیگ (`/etc/wal-g/*`) را از محل امن بازیابی کنید.
2.  **توقف سرویس و پاک‌سازی:**
    ```bash
    sudo systemctl stop postgresql
    sudo -u postgres rm -rf /var/lib/postgresql/14/main/*
    ```
3.  **بازیابی آخرین بکاپ:**
    ```bash
    sudo -u postgres bash -c ". /etc/wal-g/walg-base-config.env && wal-g backup-fetch /var/lib/postgresql/14/main LATEST"
    ```
4.  **آماده‌سازی برای ریکاوری WAL:**
    - فایل `recovery.signal` را ایجاد کنید: `sudo -u postgres touch /var/lib/postgresql/14/main/recovery.signal`
    - پارامتر `restore_command` را در `postgresql.conf` فعال کنید.
5.  **شروع بازیابی:**
    ```bash
    sudo systemctl start postgresql
    sudo tail -f /var/log/postgresql/postgresql-14-main.log
    ```

### بازیابی فایل‌ها (Restic)

1.  **آماده‌سازی سرور جدید:** Restic را با اسکریپت `install.sh` نصب کنید. فایل کانفیگ (`/etc/restic/restic-env`) را از محل امن بازیابی کنید.
2.  **مشاهده لیست بکاپ‌ها (Snapshots):**
    - برای پیدا کردن شناسه (ID) بکاپ مورد نظر، لیست اسنپ‌شات‌ها را مشاهده کنید.
      ```bash
      sudo bash -c ". /etc/restic/restic-env && restic snapshots"
      ```
3.  **بازیابی:**
    - برای بازیابی آخرین بکاپ به یک مسیر مشخص (مثلاً `/tmp/restore`):
      ```bash
      sudo bash -c ". /etc/restic/restic-env && restic restore latest --target /tmp/restore"
      ```
    - برای بازیابی یک اسنپ‌شات خاص بر اساس ID:
      ```bash
      sudo bash -c ". /etc/restic/restic-env && restic restore <SNAPSHOT_ID> --target /tmp/restore"
      ```

---

## ۶. جزئیات فنی

- **زمان‌بندی (Systemd Timers):**
  - **02:00:** بکاپ کامل روزانه PostgreSQL (`walg-backup.timer`).
  - **03:00:** بکاپ روزانه فایل‌ها (`restic-backup.timer`).
  - **04:00:** حذف بکاپ‌های قدیمی PostgreSQL (`walg-retain.timer`).
  - **05:00:** حذف بکاپ‌های قدیمی فایل‌ها (`restic-prune.timer`).
- **سیاست نگهداری (Retention Policy):**
  - **WAL-G:** نگهداری ۷ بکاپ کامل اخیر.
  - **Restic:** نگهداری ۷ روزانه، ۴ هفتگی و ۳ ماهانه.
  - این مقادیر در فایل‌های `.service` مربوطه قابل تغییر هستند.

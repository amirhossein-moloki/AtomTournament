#!/bin/sh

# اگر دستوری با خطا مواجه شد، اسکریپت متوقف شود
set -e

# ---
# متغیرها
# ---
# اگر متغیر DOMAIN تنظیم نشده بود، اسکریپت را با خطا متوقف کن
: "${DOMAIN?DOMAIN environment variable is not set}"

LE_PATH="/etc/letsencrypt/live/$DOMAIN"
DH_PARAMS_PATH="/etc/letsencrypt/dhparams.pem"
DUMMY_CERT_SUBJ="/CN=localhost"

# ---
# 1. تولید فایل nginx.conf از template
# ---
echo "### Generating nginx.conf from template..."
envsubst '$DOMAIN' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# ---
# 2. ایجاد گواهی موقت (Dummy Certificate)
# ---
# Nginx بدون وجود فایل‌های گواهی، اجرا نخواهد شد.
if [ ! -f "$LE_PATH/fullchain.pem" ]; then
    echo "### No certificate found for $DOMAIN. Creating a dummy certificate..."
    mkdir -p "$LE_PATH"
    # کاربر nginx باید مالک دایرکتوری باشد تا بتواند فایل‌ها را بخواند
    # chown nginx:nginx "$LE_PATH"
    openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
        -keyout "$LE_PATH/privkey.pem" \
        -out "$LE_PATH/fullchain.pem" \
        -subj "$DUMMY_CERT_SUBJ"
fi

# ---
# 3. اجرای دستور اصلی (CMD)
# ---
# دستورات بعدی را در پس‌زمینه اجرا می‌کند.
echo "### Starting Nginx..."
exec "$@"

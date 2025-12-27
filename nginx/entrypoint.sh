#!/bin/sh
set -e  # در صورت هر خطا اسکریپت متوقف می‌شود

# --- Configuration ---
# اولین دامنه از متغیر محیطی DOMAINS به عنوان دامنه اصلی استفاده می‌شود
if [ -z "$DOMAINS" ]; then
  echo ">>> DOMAINS env not provided, defaulting to localhost to keep nginx config valid."
  export DOMAIN=localhost
else
  export DOMAIN=$(echo "$DOMAINS" | cut -d',' -f1)
fi

LE_PATH="/etc/letsencrypt/live/$DOMAIN"  # مسیر گواهی Let's Encrypt
DHPARAMS_PATH="/etc/letsencrypt/dhparams.pem"  # مسیر فایل dhparams
DUMMY_CERT_SUBJ="/CN=localhost"  # مشخصات گواهی موقت
LE_ISSUER="Let's Encrypt"

echo "### Nginx Entrypoint: Configuration"
echo "Domain for certs: $DOMAIN"
echo "Let's Encrypt Path: $LE_PATH"
echo "--------------------"

# --- Functions ---

# تابع ایجاد گواهی موقت (dummy)
create_dummy_cert() {
  if [ ! -f "$LE_PATH/privkey.pem" ] || [ ! -f "$LE_PATH/fullchain.pem" ] || [ ! -f "$LE_PATH/chain.pem" ]; then
    echo ">>> One or more certificate files are missing. Cleaning up and creating dummy certificate for $DOMAIN..."

    # پاکسازی فایل‌های ناقص و ایجاد پوشه اگر وجود ندارد
    rm -f "$LE_PATH"/*
    mkdir -p "$LE_PATH"

    # ایجاد گواهی موقت 4096 بیت با اعتبار 1 روز
    openssl req -x509 -nodes -newkey rsa:4096 -days 1 \
      -keyout "$LE_PATH/privkey.pem" \
      -out "$LE_PATH/fullchain.pem" \
      -subj "$DUMMY_CERT_SUBJ"

    # ایجاد chain.pem که Nginx برای شروع به آن نیاز دارد
    cp "$LE_PATH/fullchain.pem" "$LE_PATH/chain.pem"

    # مالکیت فایل‌ها را به nginx تغییر می‌دهیم
    echo ">>> Setting initial ownership for dummy certificate..."
    chown -R nginx:nginx /etc/letsencrypt
  else
    echo ">>> Certificate files already exist. Skipping dummy certificate creation."
  fi
}

# تابع ایجاد dhparams (امنیت Diffie-Hellman)
create_dhparams() {
  if [ ! -f "$DHPARAMS_PATH" ]; then
    echo ">>> Creating dhparams.pem (4096 bits)... This may take a while."
    openssl dhparam -out "$DHPARAMS_PATH" 4096
  fi
}

# --- Main Logic ---

# 1. اطمینان از وجود فایل‌های اولیه
create_dummy_cert
create_dhparams

# 2. Wait for Django to be ready
echo ">>> Waiting for Django server to be available..."
while ! nc -z web 8000; do
  sleep 1
done
echo ">>> Django server is ready."

# 3. تولید کانفیگ Nginx از template
# متغیر $DOMAIN از محیط گرفته می‌شود و در template جایگزین می‌شود
envsubst '$DOMAIN' < /app/nginx.conf.template > /etc/nginx/conf.d/default.conf
echo ">>> Nginx config generated from template."

# 4. اجرای Nginx در پس‌زمینه
echo ">>> Starting Nginx with initial configuration..."
nginx -g "daemon off;" &
NGINX_PID=$!

# 4. حلقه دائمی برای اعمال تغییرات گواهی‌ها
# توضیح: این حلقه هر ۱۲ ساعت مالکیت فایل‌ها را به nginx می‌دهد و Nginx را reload می‌کند
(
  while true; do
    echo ">>> [Cron] Waiting for 12 hours before the next check..."
    sleep 12h

    echo ">>> [Cron] Updating certificate ownership for Nginx..."
    chown -R nginx:nginx /etc/letsencrypt

    echo ">>> [Cron] Reloading Nginx to apply new certificates..."
    nginx -s reload
  done
) &

# 5. نگه داشتن پروسس اصلی
wait $NGINX_PID
exit $?

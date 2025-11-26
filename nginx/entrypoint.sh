#!/bin/sh

set -e

# --- Configuration ---
# اولین دامنه از متغیر محیطی DOMAINS به عنوان دامنه اصلی استفاده می‌شود
export DOMAIN=$(echo "$DOMAINS" | cut -d',' -f1)
LE_PATH="/etc/letsencrypt/live/$DOMAIN"
DHPARAMS_PATH="/etc/letsencrypt/dhparams.pem"
DUMMY_CERT_SUBJ="/CN=localhost"
LE_ISSUER="Let's Encrypt"

echo "### Nginx Entrypoint: Configuration"
echo "Domain for certs: $DOMAIN"
echo "Let's Encrypt Path: $LE_PATH"
echo "--------------------"

# --- Functions ---
create_dummy_cert() {
  if [ ! -f "$LE_PATH/fullchain.pem" ]; then
    echo ">>> Creating dummy certificate for $DOMAIN..."
    mkdir -p "$LE_PATH"
    openssl req -x509 -nodes -newkey rsa:4096 -days 1 \
      -keyout "$LE_PATH/privkey.pem" \
      -out "$LE_PATH/fullchain.pem" \
      -subj "$DUMMY_CERT_SUBJ"

    # اطمینان از اینکه Nginx می‌تواند گواهی موقت را بخواند
    echo ">>> Setting initial ownership for dummy certificate..."
    chown -R nginx:nginx /etc/letsencrypt
  fi
}

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

# 2. تولید کانفیگ Nginx از template
# متغیر $DOMAIN از محیط گرفته می‌شود و در template جایگزین می‌شود
envsubst '$DOMAIN' < /app/nginx.conf.template > /etc/nginx/conf.d/default.conf
echo ">>> Nginx config generated from template."

# 3. راه‌اندازی Nginx در پس‌زمینه
echo ">>> Starting Nginx with initial configuration..."
# Nginx را در پس‌زمینه اجرا می‌کنیم تا بتوانیم لاگ‌ها را ببینیم
nginx -g "daemon off;" &
NGINX_PID=$!

# 4. حلقه هوشمند برای مدیریت گواهی‌ها
(
  while true; do
    echo ">>> [inotify] Watching for changes in $LE_PATH..."
    # منتظر رویداد create یا modify در پوشه گواهی‌ها می‌مانیم
    # inotifywait به طور خودکار خارج می‌شود وقتی رویدادی رخ دهد
    inotifywait -e create -e modify --timeout 43200 "$LE_PATH"

    # بعد از هر رویداد یا تایم‌اوت (۱۲ ساعت)، مالکیت را اصلاح و Nginx را reload می‌کنیم
    echo ">>> [inotify] Change detected or timeout reached. Updating permissions..."
    chown -R nginx:nginx /etc/letsencrypt

    echo ">>> [inotify] Reloading Nginx to apply changes..."
    nginx -s reload
  done
) &

# 5. نگه داشتن پروسس اصلی
wait $NGINX_PID
exit $?

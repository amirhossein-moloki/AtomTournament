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
nginx -g "daemon off;" &
NGINX_PID=$!

# 4. حلقه برای انتظار و بارگذاری گواهی واقعی
(
  echo ">>> Waiting for the real certificate to be issued by Certbot..."
  # این حلقه هر ۵ ثانیه چک می‌کند تا زمانی که گواهی واقعی صادر شود
  while ! openssl x509 -in "$LE_PATH/fullchain.pem" -noout -issuer | grep -q "$LE_ISSUER"; do
    sleep 5
  done

  echo ">>> Real certificate found. Reloading Nginx..."
  nginx -s reload
) &

# 5. حلقه برای reload دوره‌ای جهت تمدید گواهی
(
  while true; do
    echo ">>> Sleeping for 12 hours before next renewal check..."
    sleep 12h
    echo ">>> Periodically reloading Nginx to apply renewed certificates..."
    nginx -s reload
  done
) &

# 6. نگه داشتن پروسس اصلی
wait $NGINX_PID
exit $?

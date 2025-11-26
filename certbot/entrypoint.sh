#!/bin/sh

set -e

# --- Configuration ---
DOMAIN_ARGS=""
# خواندن دامنه‌ها از متغیر محیطی DOMAINS (جدا شده با کاما)
for d in $(echo "$DOMAINS" | tr ',' ' '); do
  DOMAIN_ARGS="$DOMAIN_ARGS -d $d"
done

# اولین دامنه به عنوان نام اصلی گواهی در نظر گرفته می‌شود
FIRST_DOMAIN=$(echo "$DOMAINS" | cut -d',' -f1)
LE_PATH="/etc/letsencrypt/live/$FIRST_DOMAIN"
# آدرس Nginx برای بررسی در دسترس بودن
NGINX_HOST="nginx"

echo "### Certbot Entrypoint: Configuration"
echo "Domains: $DOMAINS"
echo "Email: $EMAIL"
echo "Let's Encrypt Path: $LE_PATH"
echo "--------------------"

# --- Main Logic ---

# 1. انتظار برای آماده شدن Nginx
echo ">>> Waiting for Nginx to be available..."
# با استفاده از nc (netcat) وضعیت پورت ۸۰ را چک می‌کنیم
while ! nc -z $NGINX_HOST 80; do
  echo ">>> Nginx is not yet available, sleeping for 5 seconds..."
  sleep 5
done
echo ">>> Nginx is up and running."

# 2. دریافت گواهی اولیه (در صورت عدم وجود)
if [ ! -f "$LE_PATH/fullchain.pem" ]; then
  echo ">>> Certificate not found. Requesting a new one..."

  certbot certonly \
    --webroot -w /var/www/certbot \
    --non-interactive \
    --agree-tos \
    --email "$EMAIL" \
    $DOMAIN_ARGS \
    --rsa-key-size 4096 \
    --verbose \
    --keep-until-expiring

  if [ $? -ne 0 ]; then
    echo "!!! Certbot failed to obtain the certificate. Please check the logs."
    # در صورت خطا، اسکریپت خارج می‌شود تا از حلقه‌های بیهوده جلوگیری شود
    exit 1
  fi

  echo ">>> Certificate obtained successfully."
else
  echo ">>> Certificate already exists. Skipping initial request."
fi

# 3. حلقه برای تمدید خودکار
echo ">>> Starting renewal loop..."
while true; do
  echo ">>> Sleeping for 12 hours..."
  sleep 12h
  echo ">>> Renewing certificate..."
  certbot renew --quiet
done

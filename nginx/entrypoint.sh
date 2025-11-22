#!/bin/sh
set -eu

# اگر متغیرهای محیطی برای Nginx داری، اینجا تعریف پیش‌فرض:
: "${NGINX_HOST:=localhost}"
: "${NGINX_PORT:=80}"
: "${UPSTREAM_HOST:=web}"
: "${UPSTREAM_PORT:=8000}"

# ساخت فایل کانفیگ نهایی از روی template
envsubst '$NGINX_HOST $NGINX_PORT $UPSTREAM_HOST $UPSTREAM_PORT' \
  < /etc/nginx/conf.d/default.conf.template \
  > /etc/nginx/conf.d/default.conf

echo "Using NGINX_HOST=$NGINX_HOST NGINX_PORT=$NGINX_PORT UPSTREAM=${UPSTREAM_HOST}:${UPSTREAM_PORT}"
nginx -t || exit 1

# اجرای Nginx در foreground
exec nginx -g 'daemon off;'

# syntax=docker/dockerfile:1

##############################
# Stage 0: Build arguments
##############################

# نسخه‌ای از Nginx که با ngx_brotli تست‌شده و پایدارتره
ARG NGINX_VERSION=1.25.3
# یک commit شناخته‌شده از google/ngx_brotli
ARG BROTLI_COMMIT=6e975bc

##############################
# Stage 1: Build Nginx + Brotli
##############################
FROM alpine:3.19 AS builder

# دوباره تعریف برای استفاده داخل این stage
ARG NGINX_VERSION
ARG BROTLI_COMMIT

# ابزارهای لازم برای کامپایل
RUN apk add --no-cache \
    build-base \
    curl \
    git \
    linux-headers \
    openssl-dev \
    pcre2-dev \
    zlib-dev

# گرفتن سورس Nginx
RUN set -eux; \
    mkdir -p /usr/src/nginx; \
    curl -fSL "https://nginx.org/download/nginx-${NGINX_VERSION}.tar.gz" \
    | tar -xzC /usr/src/nginx --strip-components=1

# کلون کردن ماژول ngx_brotli و submoduleهای آن روی یک commit ثابت
RUN git clone https://github.com/google/ngx_brotli.git /usr/src/brotli \
    && cd /usr/src/brotli \
    && git checkout "${BROTLI_COMMIT}" \
    && git submodule update --init --recursive

# رفتن داخل سورس Nginx
WORKDIR /usr/src/nginx

# کانفیگ، کامپایل و نصب Nginx با ماژول Brotli
RUN set -eux; \
    ./configure \
        --prefix=/etc/nginx \
        --sbin-path=/usr/sbin/nginx \
        --modules-path=/usr/lib/nginx/modules \
        --conf-path=/etc/nginx/nginx.conf \
        --error-log-path=/var/log/nginx/error.log \
        --http-log-path=/var/log/nginx/access.log \
        --pid-path=/var/run/nginx.pid \
        --lock-path=/var/run/nginx.lock \
        --http-client-body-temp-path=/var/cache/nginx/client_temp \
        --http-proxy-temp-path=/var/cache/nginx/proxy_temp \
        --http-fastcgi-temp-path=/var/cache/nginx/fastcgi_temp \
        --http-uwsgi-temp-path=/var/cache/nginx/uwsgi_temp \
        --http-scgi-temp-path=/var/cache/nginx/scgi_temp \
        --with-threads \
        --with-file-aio \
        --with-http_ssl_module \
        --with-http_v2_module \
        --with-http_realip_module \
        --with-http_addition_module \
        --with-http_sub_module \
        --with-http_gunzip_module \
        --with-http_gzip_static_module \
        --with-http_stub_status_module \
        --add-module=/usr/src/brotli \
    && make \
    && make install

##############################
# Stage 2: Final runtime image
##############################
FROM alpine:3.19

# لایبرری‌های لازم در runtime
RUN apk add --no-cache \
    pcre2 \
    zlib \
    openssl \
    gettext \
    ca-certificates

# کپی کردن کانفیگ Nginx و باینری از استیج build
COPY --from=builder /etc/nginx /etc/nginx
COPY --from=builder /usr/sbin/nginx /usr/sbin/nginx

# ساختن دایرکتوری‌های لازم
RUN mkdir -p /var/cache/nginx /var/log/nginx /var/run/nginx /etc/nginx/conf.d /app/nginx

# کپی کردن کانفیگ پروژه و entrypoint
COPY nginx.conf /etc/nginx/nginx.conf
COPY nginx.conf.template /etc/nginx/conf.d/default.conf.template
COPY ssl_params.conf /etc/nginx/ssl_params.conf
COPY proxy_params.conf /etc/nginx/proxy_params.conf
COPY entrypoint.sh /app/nginx/entrypoint.sh

RUN chmod +x /app/nginx/entrypoint.sh

EXPOSE 80 443

ENTRYPOINT ["/app/nginx/entrypoint.sh"]

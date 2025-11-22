# syntax=docker/dockerfile:1

##############################
# Stage 0: Build arguments
##############################

# می‌تونی موقع build این‌ها رو override کنی
ARG NGINX_VERSION=1.26.1
ARG BROTLI_COMMIT=v1.1.0

##############################
# Stage 1: Build Nginx + Brotli
##############################
FROM alpine:3.19 AS builder

# باید دوباره داخل این stage تعریف بشن تا تو RUN قابل استفاده باشن
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

# گرفتن سورس Nginx (با چک کردن خطای HTTP)
RUN set -eux; \
    curl -fSL "https://nginx.org/download/nginx-${NGINX_VERSION}.tar.gz" -o nginx.tar.gz; \
    tar -xzf nginx.tar.gz; \
    mv "nginx-${NGINX_VERSION}" /usr/src/nginx; \
    rm nginx.tar.gz

# کلون کردن Brotli (طبق چیزی که خودت داشتی)
RUN git clone --depth=1 --branch="${BROTLI_COMMIT}" https://github.com/google/brotli.git /usr/src/brotli

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
        --add-module=/usr/src/brotli/c \
    && make \
    && make install

##############################
# Stage 2: Final runtime image
##############################
FROM nginx:stable-alpine

# nginx رسمی خودش user و ساختار /etc/nginx رو داره

# باینری Nginx کامپایل‌شده رو از stage قبل بیار
COPY --from=builder /usr/sbin/nginx /usr/sbin/nginx

# کتابخانه‌های لازم (همون‌هایی که خودت کپی می‌کردی)
COPY --from=builder /lib/libpcre2-8.so.0 /lib/
COPY --from=builder /lib/libz.so.1 /lib/
COPY --from=builder /usr/lib/libssl.so.3 /usr/lib/
COPY --from=builder /usr/lib/libcrypto.so.3 /usr/lib/

# ساختن دایرکتوری‌های لازم (اگر وجود نداشتند)
RUN mkdir -p /var/cache/nginx /var/log/nginx /var/run/nginx

# کپی کردن کانفیگ پروژه و entrypoint
# توجه: nginx رسمی از /etc/nginx/nginx.conf و /etc/nginx/conf.d/*.conf استفاده می‌کند
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY entrypoint.sh /app/nginx/entrypoint.sh

RUN chmod +x /app/nginx/entrypoint.sh

EXPOSE 80 443

ENTRYPOINT ["/app/nginx/entrypoint.sh"]
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
        --add-module=/usr/src/brotli/c \
    && make \
    && make install

# Stage 2: Create the final, lean production image
FROM nginx:stable-alpine

# Copy the compiled Nginx binary from the builder stage
COPY --from=builder /usr/sbin/nginx /usr/sbin/nginx

# Copy necessary shared libraries from the builder stage to avoid runtime mismatches
COPY --from=builder /lib/libpcre2-8.so.0 /lib/
COPY --from=builder /lib/libz.so.1 /lib/
COPY --from=builder /usr/lib/libssl.so.3 /usr/lib/
COPY --from=builder /usr/lib/libcrypto.so.3 /usr/lib/

# Copy the project's Nginx configuration and entrypoint script
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY entrypoint.sh /app/nginx/entrypoint.sh

RUN chmod +x /app/nginx/entrypoint.sh

ENTRYPOINT ["/app/nginx/entrypoint.sh"]

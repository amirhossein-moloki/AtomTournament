# Dockerfile

# --- Builder Stage ---
# مرحله‌ای برای کامپایل کردن Nginx از سورس به همراه ماژول Brotli
FROM debian:bullseye-slim AS builder

# تعریف نسخه‌ها برای نگهداری آسان‌تر
ENV NGINX_VERSION 1.25.3
ENV NGX_BROTLI_COMMIT v1.1.0

# نصب ابزارهای مورد نیاز برای کامپایل
RUN apt-get update && \
    apt-get install --no-install-recommends --no-install-suggests -y \
    build-essential \
    libpcre3-dev \
    zlib1g-dev \
    libssl-dev \
    curl \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# دانلود سورس Nginx
RUN curl -L "https://nginx.org/download/nginx-${NGINX_VERSION}.tar.gz" | \
    tar -zx --strip-components=1 -C /usr/src/

# دانلود سورس ماژول Brotli
RUN git clone --depth=1 --branch ${NGX_BROTLI_COMMIT} https://github.com/google/ngx_brotli.git /usr/src/ngx_brotli && \
    cd /usr/src/ngx_brotli && \
    git submodule update --init

# کامپایل Nginx با ماژول Brotli
RUN cd /usr/src/ && \
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
    --user=nginx \
    --group=nginx \
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
    --add-module=/usr/src/ngx_brotli && \
    make -j$(nproc) && \
    make install

# --- Final Stage ---
# مرحله نهایی برای ساخت ایمیج سبک پروداکشن
FROM debian:bullseye-slim

# نصب پکیج‌های ضروری و کاربر `nginx`
RUN apt-get update && \
    apt-get install --no-install-recommends --no-install-suggests -y \
    openssl \
    gettext-base \
    && addgroup --system --gid 101 nginx \
    && adduser --system --disabled-password --ingroup nginx --no-create-home --home /nonexistent --shell /bin/false --uid 101 nginx \
    && rm -rf /var/lib/apt/lists/*

# کپی کردن فایل‌های کامپایل شده از مرحله `builder`
COPY --from=builder /etc/nginx /etc/nginx
COPY --from=builder /usr/sbin/nginx /usr/sbin/nginx
COPY --from=builder /usr/lib/nginx/modules /usr/lib/nginx/modules

# کپی کردن فایل‌های تنظیمات و اسکریپت ورودی
COPY nginx.conf.template /etc/nginx/nginx.conf.template
COPY proxy_params.conf /etc/nginx/proxy_params.conf
COPY ssl_params.conf /etc/nginx/ssl_params.conf
COPY security_headers.conf /etc/nginx/security_headers.conf
COPY entrypoint.sh /docker-entrypoint.sh

# ایجاد دایرکتوری‌های مورد نیاز و تنظیم دسترسی‌ها
RUN mkdir -p /var/cache/nginx /var/www/certbot && \
    chown -R nginx:nginx /var/cache/nginx /var/www/certbot && \
    chmod +x /docker-entrypoint.sh

# پورت‌های 80 و 443 را expose می‌کنیم
EXPOSE 80 443

# تعریف دستور ورودی
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]

# Use a base image with build tools
FROM alpine:3.14 as builder

# Install build dependencies
RUN apk add --no-cache build-base pcre-dev zlib-dev openssl-dev git

# Define Nginx version
ENV NGINX_VERSION 1.20.2

# Download and extract Nginx source
RUN wget http://nginx.org/download/nginx-${NGINX_VERSION}.tar.gz && \
    tar -zxvf nginx-${NGINX_VERSION}.tar.gz && \
    rm nginx-${NGINX_VERSION}.tar.gz

# Clone the correct Nginx Brotli module repository and initialize its submodules
RUN git clone https://github.com/eustas/ngx_brotli.git && \
    cd ngx_brotli && \
    git submodule update --init

# Build Nginx with the Brotli module
RUN cd nginx-${NGINX_VERSION} && \
    ./configure \
        --with-http_ssl_module \
        --with-http_v2_module \
        --add-module=../ngx_brotli \
        --prefix=/usr/share/nginx \
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
        --group=nginx && \
    make && \
    make install

# Final, smaller image
FROM nginx:stable-alpine

# Copy the custom Nginx build from the builder stage
COPY --from=builder /usr/sbin/nginx /usr/sbin/nginx
COPY --from=builder /etc/nginx/nginx.conf /etc/nginx/nginx.conf

# Copy the project's final nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

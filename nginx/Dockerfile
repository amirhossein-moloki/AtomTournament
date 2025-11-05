# Use a base image with build tools
FROM alpine:3.14 as builder

# Install build dependencies
RUN apk add --no-cache build-base pcre-dev zlib-dev openssl-dev git

# Define Nginx and Brotli versions
ENV NGINX_VERSION 1.20.2
ENV BROTLI_COMMIT_SHA e61b7f3630cf5638c4ef4e37f10b7b3a86241b80

# Download and extract Nginx source
RUN wget http://nginx.org/download/nginx-${NGINX_VERSION}.tar.gz && \
    tar -zxvf nginx-${NGINX_VERSION}.tar.gz && \
    rm nginx-${NGINX_VERSION}.tar.gz

# Clone Google Brotli repository
RUN git clone https://github.com/google/brotli.git && \
    cd brotli && \
    git checkout ${BROTLI_COMMIT_SHA} && \
    cd ..

# Build Nginx with Brotli module
RUN cd nginx-${NGINX_VERSION} && \
    ./configure \
        --with-http_ssl_module \
        --with-http_v2_module \
        --add-module=../brotli/nginx/ \
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

# Final image
FROM nginx:stable-alpine

# Copy the custom Nginx build from the builder stage
COPY --from=builder /usr/sbin/nginx /usr/sbin/nginx
COPY --from=builder /usr/lib/nginx/modules /usr/lib/nginx/modules
COPY --from=builder /etc/nginx/nginx.conf /etc/nginx/nginx.conf

# Copy the project's nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

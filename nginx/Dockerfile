FROM nginx:stable-alpine

RUN apk add --no-cache nginx nginx-mod-http-brotli \
    && sed -i '1iload_module modules/ngx_http_brotli_filter_module.so;\nload_module modules/ngx_http_brotli_static_module.so;' /etc/nginx/nginx.conf \
    && printf "%s\n" \
        "brotli on;" \
        "brotli_static on;" \
        "brotli_comp_level 5;" \
        "brotli_buffers 16 8k;" \
        "brotli_types text/plain text/css text/csv application/json application/javascript application/xml application/rss+xml application/ld+json application/vnd.ms-fontobject application/x-font-ttf font/opentype image/svg+xml;" \
        > /etc/nginx/conf.d/brotli.conf

COPY nginx.conf /etc/nginx/conf.d/default.conf

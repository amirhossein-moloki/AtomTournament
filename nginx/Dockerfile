FROM nginx:stable-alpine

RUN apk add --no-cache \
    nginx-mod-http-brotli \
    nginx-mod-http-brotli-static

COPY nginx.conf /etc/nginx/conf.d/default.conf

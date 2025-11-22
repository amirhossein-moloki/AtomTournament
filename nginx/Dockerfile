FROM nginx:stable-alpine

RUN apk add --no-cache openssl nginx-mod-brotli wget

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY entrypoint.sh /app/nginx/entrypoint.sh

RUN chmod +x /app/nginx/entrypoint.sh

ENTRYPOINT ["/app/nginx/entrypoint.sh"]

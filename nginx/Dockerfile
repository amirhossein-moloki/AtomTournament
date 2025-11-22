FROM fholzer/nginx-brotli:latest

# Install utilities we rely on in the entrypoint
RUN apk add --no-cache openssl wget \
    && mkdir -p /etc/nginx/modules

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY modules.conf /etc/nginx/modules/mod-http-brotli.conf
COPY entrypoint.sh /app/nginx/entrypoint.sh

RUN chmod +x /app/nginx/entrypoint.sh

ENTRYPOINT ["/app/nginx/entrypoint.sh"]

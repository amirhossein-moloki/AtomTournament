FROM fholzer/nginx-brotli:latest

# Install utilities we rely on in the entrypoint
RUN apk add --no-cache openssl wget gettext inotify-tools \
    && mkdir -p /etc/nginx/modules

COPY nginx.conf.template /app/nginx.conf.template
COPY modules.conf /etc/nginx/modules/mod-http-brotli.conf
COPY entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]

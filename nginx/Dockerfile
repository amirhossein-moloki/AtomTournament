FROM nginx:stable-alpine

# Install required packages. The brotli module is provided from the edge
# community repository on Alpine, so we explicitly point apk there to avoid
# package resolution failures on newer Alpine versions.
RUN apk add --no-cache openssl wget \
    && apk add --no-cache --repository=https://dl-cdn.alpinelinux.org/alpine/edge/community \
       nginx-mod-http-brotli \
    && mkdir -p /etc/nginx/modules

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY modules.conf /etc/nginx/modules/mod-http-brotli.conf
COPY entrypoint.sh /app/nginx/entrypoint.sh

RUN chmod +x /app/nginx/entrypoint.sh

ENTRYPOINT ["/app/nginx/entrypoint.sh"]

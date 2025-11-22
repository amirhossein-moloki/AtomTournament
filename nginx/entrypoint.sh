#!/bin/sh

set -eu

DOMAIN=${DOMAIN:-atom-game.ir}
CONFIG_TEMPLATE=/etc/nginx/conf.d/default.conf.template
CONFIG_PATH=/etc/nginx/conf.d/default.conf
LE_PATH="/etc/letsencrypt/live/$DOMAIN"

log() {
    printf '%s %s\n' "[nginx-entrypoint]" "$*"
}

render_config() {
    export DOLLAR='$'
    envsubst '${DOMAIN}' < "$CONFIG_TEMPLATE" > "$CONFIG_PATH"
}

ensure_dummy_cert() {
    if [ -f "$LE_PATH/fullchain.pem" ]; then
        return
    fi

    log "Creating dummy certificate for $DOMAIN ..."
    mkdir -p "$LE_PATH"
    openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
        -keyout "$LE_PATH/privkey.pem" \
        -out "$LE_PATH/fullchain.pem" \
        -subj "/CN=localhost"
}

wait_for_real_cert_and_reload() {
    log "Waiting for certificate for $DOMAIN ..."
    while ! openssl x509 -in "$LE_PATH/fullchain.pem" -noout -issuer 2>/dev/null | grep -q "Let's Encrypt"; do
        sleep 5
    done

    log "Certificate for $DOMAIN found, reloading Nginx ..."
    nginx -s reload
}

start_nginx() {
    log "Starting Nginx ..."
    nginx -g "daemon off;"
}

main() {
    render_config
    ensure_dummy_cert
    wait_for_real_cert_and_reload &
    start_nginx
}

main "$@"

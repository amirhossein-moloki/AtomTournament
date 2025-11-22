#!/bin/sh

set -e

# Variables
domain="atom-game.ir"
le_path="/etc/letsencrypt/live/$domain"
dummy_cert_subj="/CN=localhost"
le_issuer="Let's Encrypt"

# 1. Create a dummy certificate to allow Nginx to start
if [ ! -f "$le_path/fullchain.pem" ]; then
    echo "### Creating dummy certificate for $domain ..."
    mkdir -p "$le_path"
    openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
        -keyout "$le_path/privkey.pem" \
        -out "$le_path/fullchain.pem" \
        -subj "$dummy_cert_subj"
fi

# 2. Start Nginx in the background
echo "### Starting Nginx..."
nginx -g "daemon off;" &

# 3. Fast-polling loop to wait for the real certificate
echo "### Waiting for the real certificate to be issued by Certbot..."
while ! openssl x509 -in "$le_path/fullchain.pem" -noout -issuer | grep -q "$le_issuer"; do
    sleep 5
done

# 4. Reload Nginx as soon as the real certificate is found
echo "### Real certificate found. Reloading Nginx..."
nginx -s reload

# 5. Start a slow-polling loop in the background for future renewals
(
    while true; do
        echo "### Waiting for 12 hours before next renewal check..."
        sleep 12h
        echo "### Checking for certificate renewal and reloading Nginx..."
        nginx -s reload
    done
) &

# 6. Keep the main process running
wait

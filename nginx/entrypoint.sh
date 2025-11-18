#!/bin/sh

set -e

# Paths
domain="atom-game.ir"
le_path="/etc/letsencrypt/live/$domain"

# Create dummy cert if it doesn't exist, to allow nginx to start
if [ ! -f "$le_path/fullchain.pem" ]; then
    echo "### Creating dummy certificate for $domain ..."
    mkdir -p "$le_path"
    openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
        -keyout "$le_path/privkey.pem" \
        -out "$le_path/fullchain.pem" \
        -subj "/CN=localhost"
fi

# Start a process that reloads Nginx every 12 hours in the background
(while true; do sleep 12h; echo "### Reloading Nginx to pick up new certificates..."; nginx -s reload; done) &

# Start Nginx in the foreground
echo "### Starting Nginx..."
nginx -g "daemon off;"

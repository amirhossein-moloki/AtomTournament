#!/bin/sh

set -e

# Use environment variable for domain, with a default value
DOMAIN=${DOMAIN:-atom-game.ir}

# Replace placeholders in the template to create the final config
# We only want to substitute ${DOMAIN}, not other shell variables like $host
export DOLLAR='$'
envsubst '${DOMAIN}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf


# Paths
le_path="/etc/letsencrypt/live/$DOMAIN"

# Create dummy cert if it doesn't exist, to allow nginx to start
if [ ! -f "$le_path/fullchain.pem" ]; then
    echo "### Creating dummy certificate for $DOMAIN ..."
    mkdir -p "$le_path"
    openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
        -keyout "$le_path/privkey.pem" \
        -out "$le_path/fullchain.pem" \
        -subj "/CN=localhost"
fi

# Start a background process to reload Nginx once the real certificate is issued
(
  echo "### Waiting for certificate for $DOMAIN..."
  while ! openssl x509 -in "$le_path/fullchain.pem" -noout -issuer | grep -q "Let's Encrypt"; do
    sleep 5
  done
  echo "### Certificate for $DOMAIN found, reloading Nginx..."
  nginx -s reload
) &

# Start Nginx in the foreground
echo "### Starting Nginx..."
nginx -g "daemon off;"

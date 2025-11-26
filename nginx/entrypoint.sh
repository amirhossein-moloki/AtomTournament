#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# ---
# Graceful Shutdown
# ---
# On script exit, kill the Nginx process.
trap 'kill $(jobs -p)' EXIT

# ---
# Permissions Fix for Certbot
# ---
# Certbot runs as root and Nginx runs as nginx.
# This ensures that Nginx can read the challenge files created by Certbot.
echo "### Ensuring correct permissions for Certbot challenge directory..."
mkdir -p /var/www/certbot
# Set ownership to the nginx user
chown -R nginx:nginx /var/www/certbot
# Set permissions to be readable and executable by all
chmod -R 755 /var/www/certbot

# ---
# Variables
# ---
DOMAIN="atom-game.ir"
LE_PATH="/etc/letsencrypt/live/$DOMAIN"
DUMMY_CERT_SUBJ="/CN=localhost"
LE_ISSUER="Let's Encrypt"

# ---
# 1. Create a Dummy Certificate to Allow Nginx to Start
# ---
# Nginx will fail to start if the certificate files are missing.
# We create a self-signed certificate as a placeholder.
if [ ! -f "$LE_PATH/fullchain.pem" ]; then
    echo "### No certificate found. Creating a dummy certificate for $DOMAIN..."
    mkdir -p "$LE_PATH"
    openssl req -x509 -nodes -newkey rsa:4096 -days 1 \
        -keyout "$LE_PATH/privkey.pem" \
        -out "$LE_PATH/fullchain.pem" \
        -subj "$DUMMY_CERT_SUBJ"
    # Create the chain file needed for OCSP stapling
    cp "$LE_PATH/fullchain.pem" "$LE_PATH/chain.pem"

    echo "### Setting ownership of dummy certificate..."
    chown -R nginx:nginx "$LE_PATH"
fi

# ---
# 2. Start Nginx in the Background
# ---
echo "### Starting Nginx in the background..."
# The 'daemon off;' directive is necessary to keep Nginx running in the foreground
# within the container, but we use '&' to background it within the script.
nginx -g "daemon off;" &
# Capture the Process ID (PID) of the Nginx process
nginx_pid=$!

# ---
# 3. Wait for the Real Certificate from Certbot
# ---
# This loop polls the certificate file until its issuer changes from our
# dummy 'localhost' to the real 'Let's Encrypt' issuer.
echo "### Waiting for the real certificate to be issued by Certbot..."
while ! openssl x509 -in "$LE_PATH/fullchain.pem" -noout -issuer | grep -q "$LE_ISSUER"; do
    # Check if Nginx is still running. If not, exit the script.
    if ! kill -0 $nginx_pid 2>/dev/null; then
        echo "!!! Nginx process died while waiting for certificate. Exiting." >&2
        exit 1
    fi
    sleep 5
done

# ---
# 4. Reload Nginx with the Real Certificate
# ---
# Once the real certificate is available, reload Nginx to apply it.
echo "### Real certificate found. Reloading Nginx..."
nginx -s reload

# ---
# 5. Start Background Renewal Loop
# ---
# This loop runs indefinitely to periodically reload Nginx,
# ensuring it picks up renewed certificates from Certbot.
(
    while true; do
        echo "### Renewal check loop: waiting 12 hours..."
        sleep 12h
        echo "### Reloading Nginx to apply any renewed certificates..."
        nginx -s reload
    done
) &

# ---
# 6. Wait for Nginx to Exit
# ---
# The 'wait' command blocks the script from exiting as long as the Nginx
# process is running. If Nginx crashes, the script will exit.
wait $nginx_pid

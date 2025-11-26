#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Environment Variables ---
# DOMAIN: The domain name for which to obtain the certificate (e.g., example.com)
# EMAIL: The email address for Let's Encrypt registration and recovery
# NGINX_CONF_TEMPLATE: Path to the Nginx configuration template
# NGINX_CONF_OUTPUT: Path to the final Nginx configuration file
# SSL_CERT_PATH: Path to the full chain certificate
# SSL_KEY_PATH: Path to the private key

DOMAIN="${DOMAIN?Error: DOMAIN environment variable is not set.}"
NGINX_CONF_TEMPLATE="/etc/nginx/templates/app.conf.template"
NGINX_CONF_OUTPUT="/etc/nginx/conf.d/default.conf"
LETSENCRYPT_DIR="/etc/letsencrypt/live/${DOMAIN}"
SSL_CERT_PATH="${LETSENCRYPT_DIR}/fullchain.pem"
SSL_KEY_PATH="${LETSENCRYPT_DIR}/privkey.pem"

# --- Functions ---

# Function to generate a self-signed certificate for initial startup
generate_self_signed_cert() {
  echo ">>> Generating self-signed certificate for ${DOMAIN}..."
  mkdir -p "${LETSENCRYPT_DIR}"
  openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
    -keyout "${SSL_KEY_PATH}" \
    -out "${SSL_CERT_PATH}" \
    -subj "/CN=${DOMAIN}"
  echo ">>> Self-signed certificate generated."
}

# Function to generate Nginx configuration from the template
generate_nginx_config() {
  echo ">>> Generating Nginx configuration..."
  # Use envsubst to replace ${DOMAIN} in the template file
  # The dollar signs in the template need to be escaped for envsubst to ignore them
  # if they are not meant to be environment variables.
  export DOLLAR='$'
  envsubst < "${NGINX_CONF_TEMPLATE}" > "${NGINX_CONF_OUTPUT}"
  echo ">>> Nginx configuration generated at ${NGINX_CONF_OUTPUT}."
}

# Function to watch for certificate updates and reload Nginx
watch_certificates() {
  echo ">>> Starting certificate watcher in the background..."
  while true; do
    # Wait for any change in the certificate directory
    # -e create: Watch for new files (initial certificate)
    # -e modify: Watch for modifications (renewals)
    # -e delete: Watch for deletions
    inotifywait -e create -e modify -e delete --recursive --timeout 3600 "${LETSENCRYPT_DIR}"
    echo ">>> Certificate change detected. Reloading Nginx..."
    # Reload Nginx gracefully
    nginx -s reload
    echo ">>> Nginx reloaded."
  done
}

# --- Main Execution ---

# 1. Initial Certificate Check
# If the Let's Encrypt certificate does not exist, create a self-signed one
# to allow Nginx to start up successfully.
if [ ! -f "${SSL_CERT_PATH}" ]; then
  generate_self_signed_cert
fi

# 2. Generate the initial Nginx configuration
generate_nginx_config

# 3. Start the certificate watcher in the background
watch_certificates &

# 4. Start the main Nginx process
# `exec "$@"` is important to ensure that the Nginx process becomes PID 1
# in the container, allowing it to receive signals correctly (e.g., from `docker stop`).
echo ">>> Starting Nginx..."
exec "$@"

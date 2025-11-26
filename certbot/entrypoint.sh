#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Environment Variables ---
# DOMAIN: The domain name for which to obtain the certificate (e.g., example.com)
# EMAIL: The email address for Let's Encrypt registration and recovery
# STAGING: Set to "1" to use Let's Encrypt's staging environment for testing.
#          Defaults to production if not set.

DOMAIN="${DOMAIN?Error: DOMAIN environment variable is not set.}"
EMAIL="${EMAIL?Error: EMAIL environment variable is not set.}"
STAGING="${STAGING:-0}" # Default to 0 (production) if not set

# --- Certbot Configuration ---
LETSENCRYPT_DIR="/etc/letsencrypt/live/${DOMAIN}"
CERT_PATH="${LETSENCRYPT_DIR}/fullchain.pem"
WEBROOT_PATH="/var/www/certbot"
RENEWAL_INTERVAL="12h" # Check for renewal twice a day

# --- Main Logic ---

# Check if a certificate already exists.
if [ -f "${CERT_PATH}" ]; then
  echo ">>> Certificate already exists for ${DOMAIN}. Proceeding with renewal checks."
else
  echo ">>> No certificate found for ${DOMAIN}. Attempting to obtain one..."

  # Determine whether to use the staging or production environment.
  if [ "${STAGING}" = "1" ]; then
    echo ">>> Using Let's Encrypt staging environment."
    STAGING_FLAG="--staging"
  else
    echo ">>> Using Let's Encrypt production environment."
    STAGING_FLAG=""
  fi

  # Request the certificate using the webroot authenticator.
  # --agree-tos: Agree to the Terms of Service.
  # --no-eff-email: Do not subscribe to the EFF newsletter.
  # -d: Specify the domain(s).
  certbot certonly \
    --webroot \
    --webroot-path="${WEBROOT_PATH}" \
    --email "${EMAIL}" \
    --agree-tos \
    --no-eff-email \
    ${STAGING_FLAG} \
    -d "${DOMAIN}"

  echo ">>> Certificate obtained successfully."
fi

# --- Renewal Loop ---
# This loop will run indefinitely to handle automatic renewals.
echo ">>> Starting automatic renewal process. Checking every ${RENEWAL_INTERVAL}."
while true; do
  # The `certbot renew` command will automatically check if the certificate
  # is due for renewal. If it is, it will renew it. Otherwise, it does nothing.
  certbot renew
  echo ">>> Renewal check complete. Next check in ${RENEWAL_INTERVAL}."
  sleep "${RENEWAL_INTERVAL}"
done

#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Generate the MD5 hash for the user's password.
# PostgreSQL's MD5 hash is the string "md5" followed by the MD5 hash of the password concatenated with the username.
PASSWORD_HASH=$(echo -n "${POSTGRES_PASSWORD}${POSTGRES_USER}" | md5sum | awk '{print $1}')
MD5_HASH="md5${PASSWORD_HASH}"

# Create the final userlist.txt from the template.
# We use sed to replace the dummy username and password hash with the real ones.
sed -e "s/\"dummyuser\"/\"${POSTGRES_USER}\"/" \
    -e "s/\"dummypass\"/\"${MD5_HASH}\"/" \
    /etc/pgbouncer/userlist.txt.template > /etc/pgbouncer/userlist.txt

# PGBouncer needs read-only access to this file.
chmod 644 /etc/pgbouncer/userlist.txt

# Start PgBouncer with the specified config file.
# The `pgbouncer` user is created by the official image.
# We use `exec` to replace the shell process with the pgbouncer process.
echo "Starting PgBouncer..."
exec pgbouncer /etc/pgbouncer/pgbouncer.ini

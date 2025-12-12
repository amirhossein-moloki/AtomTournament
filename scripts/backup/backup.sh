#!/bin/bash
set -euo pipefail

# --- Configuration ---
# Load only necessary variables from .env file to avoid export issues
if [ -f .env ]; then
    source .env
fi

# Database connection details
PG_USER="${POSTGRES_USER:-your-db-user}"
PG_DB="${POSTGRES_DB:-your-db-name}"
PG_PASSWORD="${POSTGRES_PASSWORD:-your-db-password}"
PG_HOST="db" # Always connect to the 'db' service directly for backups

# Backup directory
BACKUP_DIR="$(pwd)/backups"
mkdir -p "$BACKUP_DIR"

# Timestamp for the backup file
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_FILENAME="dump_${TIMESTAMP}.sql.gz"
BACKUP_FILEPATH="${BACKUP_DIR}/${BACKUP_FILENAME}"

# --- Main Backup Logic ---
echo "Starting database backup..."
echo "  DB User: ${PG_USER}"
echo "  DB Name: ${PG_DB}"
echo "  Output File: ${BACKUP_FILEPATH}"

# Use docker-compose to execute pg_dump inside the db container.
# The output is compressed with gzip and redirected to the host machine.
# We use a custom format (-Fc) which is flexible and can be used with pg_restore.
sudo docker compose exec -T \
    -e PGPASSWORD="${PG_PASSWORD}" \
    db \
    pg_dump -U "$PG_USER" -d "$PG_DB" -h "$PG_HOST" --format=custom | gzip > "$BACKUP_FILEPATH"

# --- Verification ---
if [ ${PIPESTATUS[0]} -eq 0 ] && [ -s "$BACKUP_FILEPATH" ]; then
    echo "✅ Backup successfully created: ${BACKUP_FILEPATH}"
    # Optional: Clean up old backups (e.g., keep the last 7)
    # find "$BACKUP_DIR" -name "dump_*.sql.gz" -mtime +7 -delete
else
    echo "❌ Backup failed."
    # Clean up the failed (potentially empty) backup file
    rm -f "$BACKUP_FILEPATH"
    exit 1
fi

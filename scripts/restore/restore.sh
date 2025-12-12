#!/bin/bash
set -euo pipefail

# --- Configuration ---
# Load only necessary variables from .env file to avoid export issues
if [ -f .env ]; then
    source .env
fi

# Target database for restore (we use a temporary name to avoid overwriting the main DB)
RESTORE_DB_NAME="restore_test_db"
PG_USER="${POSTGRES_USER:-your-db-user}"
PG_PASSWORD="${POSTGRES_PASSWORD:-your-db-password}"
PG_HOST="db"

# Input backup file
BACKUP_FILE=$1
if [ -z "$BACKUP_FILE" ]; then
    echo "❌ Error: Please provide the path to the backup file as the first argument."
    echo "Usage: $0 /path/to/your/dump.sql.gz"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Error: Backup file not found at ${BACKUP_FILE}"
    exit 1
fi

# --- Main Restore Logic ---
echo "Starting database restore process..."
echo "  Source File: ${BACKUP_FILE}"
echo "  Target DB: ${RESTORE_DB_NAME}"

# Set the password for pg commands
export PGPASSWORD="${PG_PASSWORD}"

# Step 1: Drop the test database if it exists to ensure a clean restore.
echo "Dropping existing test database (if any)..."
sudo docker compose exec -T db dropdb -U "$PG_USER" -h "$PG_HOST" "$RESTORE_DB_NAME" --if-exists

# Step 2: Create a new, empty database for the restore.
echo "Creating new test database..."
sudo docker compose exec -T db createdb -U "$PG_USER" -h "$PG_HOST" "$RESTORE_DB_NAME"

# Step 3: Restore the backup into the new database using pg_restore.
# We pipe the gzipped backup file into the container.
echo "Restoring data from backup..."
gunzip < "$BACKUP_FILE" | sudo docker compose exec -T db pg_restore -U "$PG_USER" -h "$PG_HOST" -d "$RESTORE_DB_NAME"

# --- Verification ---
if [ ${PIPESTATUS[1]} -eq 0 ]; then
    echo "✅ Restore completed successfully."
    echo "A test database named '${RESTORE_DB_NAME}' is now available for inspection."
else
    echo "❌ Restore failed."
    exit 1
fi

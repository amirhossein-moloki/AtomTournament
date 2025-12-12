#!/bin/bash
set -euo pipefail

# --- Configuration ---
# Load only necessary variables from .env file to avoid export issues
if [ -f .env ]; then
    source .env
fi

# The test database created by the restore script
TEST_DB_NAME="restore_test_db"
PG_USER="${POSTGRES_USER:-your-db-user}"
PG_PASSWORD="${POSTGRES_PASSWORD:-your-db-password}"
PG_HOST="db"

# --- Main Test Logic ---
echo "Starting smoke test on restored database '${TEST_DB_NAME}'..."

# Set the password for psql
export PGPASSWORD="${PG_PASSWORD}"

# Function to execute a query and check the result
run_query() {
    local query=$1
    local description=$2

    echo -n "  - Testing: ${description}... "

    # Execute the query. Use -Atq to get a clean, single-line output.
    result=$(sudo docker compose exec -T db psql -U "$PG_USER" -h "$PG_HOST" -d "$TEST_DB_NAME" -tAc "$query")

    # Check if the query executed successfully and returned a plausible result
    if [ $? -eq 0 ] && [ ! -z "$result" ] && [ "$result" -ge 0 ]; then
        echo "✅ OK (Result: $result)"
    else
        echo "❌ FAILED"
        echo "    Query: ${query}"
        echo "    Result: ${result}"
        # Clean up and exit
        cleanup 1
    fi
}

# --- Smoke Tests ---
# Test 1: Simple connection test
run_query "SELECT 1;" "Connection to database"

# Test 2: Check if django_migrations table exists and has data.
# This confirms that the schema and initial data were restored.
run_query "SELECT COUNT(*) FROM django_migrations WHERE app = 'users';" "Presence of 'users' app migrations"

# Test 3: Check for users in the database (adjust table/condition if needed).
# The count should be >= 1 (at least an admin user).
run_query "SELECT COUNT(*) FROM users_user;" "User data is present"

# --- Cleanup ---
cleanup() {
    local exit_code=$1
    echo "Cleaning up test database..."
    sudo docker compose exec -T db dropdb -U "$PG_USER" -h "$PG_HOST" "$TEST_DB_NAME" --if-exists
    echo "Cleanup complete."
    exit "$exit_code"
}

echo "All smoke tests passed successfully."
cleanup 0

# Makefile for common project tasks

.PHONY: help backup test-restore

help:
	@echo "Available commands:"
	@echo "  make backup        - Creates a new compressed backup of the database in the 'backups/' directory."
	@echo "  make test-restore  - Creates a backup, restores it to a temporary database, and runs smoke tests to verify integrity."

backup:
	@echo "--> Creating database backup..."
	@scripts/backup/backup.sh

test-restore:
	@echo "--> Ensuring services are running..."
	@sudo docker compose up -d --wait
	@echo "\n--> Starting backup and restore smoke test..."
	@echo "Step 1: Creating a temporary backup..."
	@scripts/backup/backup.sh
	@LATEST_BACKUP=$$(ls -t backups/dump_*.sql.gz | head -n 1)
	@echo "Step 2: Restoring backup file: $$LATEST_BACKUP"
	@scripts/restore/restore.sh $$LATEST_BACKUP
	@echo "Step 3: Running smoke tests on the restored database..."
	@scripts/restore/smoke_test.sh
	@echo "--> Backup and restore process completed successfully."

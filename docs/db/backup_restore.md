# Database Backup and Restore Procedures

This document outlines the procedures for backing up and restoring the application's PostgreSQL database.

## 1. Overview

We have a set of scripts and a `Makefile` to automate the process of creating database backups and, more importantly, testing that those backups can be successfully restored.

-   **Backup Script**: `scripts/backup/backup.sh`
-   **Restore Script**: `scripts/restore/restore.sh`
-   **Verification Script**: `scripts/restore/smoke_test.sh`

All backups are stored in the `backups/` directory at the root of the project. **This directory is included in `.gitignore` and should not be committed to version control.**

## 2. Manual Backup

To create a single, compressed backup of the database, run the following `make` command:

```bash
make backup
```

This command will:
1.  Execute the `scripts/backup/backup.sh` script.
2.  Connect to the running `db` container.
3.  Use `pg_dump` to create a compressed backup file in the `custom` format.
4.  Save the file to the `backups/` directory with a timestamp, e.g., `backups/dump_2025-12-12_17-30-00.sql.gz`.

## 3. Automated Restore Testing

The most critical part of a backup strategy is ensuring the backups actually work. We have an automated process for this.

To test the entire backup and restore cycle, run:

```bash
make test-restore
```

This command performs the following sequence of actions:
1.  **Create a fresh backup** of the current database using the `backup` command.
2.  **Restore the backup** to a **new, temporary database** named `restore_test_db`. This ensures the main development database is never touched or overwritten.
3.  **Run smoke tests** (`smoke_test.sh`) against the restored database to verify its integrity. The tests check for:
    -   Basic connectivity.
    -   The presence of key tables (like `django_migrations`).
    -   The existence of data (e.g., at least one user).
4.  **Clean up** by deleting the temporary `restore_test_db` after the tests are complete.

If this command completes successfully, you can have high confidence that your backup process is working correctly.

## 4. Manual Restore (Emergency)

To manually restore a backup (for example, in a disaster recovery scenario or to populate a new development machine), you can use the `restore.sh` script directly.

```bash
# Example: Restore the latest backup
LATEST_BACKUP=$(ls -t backups/dump_*.sql.gz | head -n 1)
scripts/restore/restore.sh $LATEST_BACKUP
```

This will create the `restore_test_db`. You would then need to manually point your application to this database or rename it as needed.

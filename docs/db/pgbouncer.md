# PgBouncer for Connection Pooling

This document explains the setup and operational guide for PgBouncer, our connection pooler for PostgreSQL.

## 1. Overview

PgBouncer is a lightweight connection pooler for PostgreSQL. It sits between our Django application and the PostgreSQL database. Instead of each application process creating its own expensive database connection, PgBouncer maintains a pool of open connections to the database and assigns them to application clients as needed.

This approach significantly reduces the overhead of creating new connections, lowers memory usage on the database server, and prevents connection exhaustion under high load.

We are using **Transaction Pooling** (`pool_mode = transaction`), which is the safest choice for Django. This means a database connection is assigned to a client for the duration of a single transaction.

## 2. Configuration

- **`docker-compose.yml`**: Defines the `pgbouncer` service.
- **`pgbouncer/pgbouncer.ini`**: The main configuration file.
- **`pgbouncer/userlist.txt.template`**: A template for the user authentication file.
- **`pgbouncer/entrypoint.sh`**: A script that generates the final `userlist.txt` from environment variables at container startup.

## 3. Environment Variables

Our setup uses two environment variables to manage database connections:

- **`DATABASE_URL`**:
  - `postgres://<user>:<password>@pgbouncer:5432/<db>`
  - This is the **default URL** the application should use. It points to the PgBouncer service, ensuring all application traffic goes through the connection pooler.

- **`DATABASE_URL_DIRECT`**:
  - `postgres://<user>:<password>@db:5432/<db>`
  - This URL connects **directly to the PostgreSQL database**, bypassing PgBouncer.

### When to use `DATABASE_URL_DIRECT`

You should use the direct connection for tasks that are incompatible with transaction pooling or require a persistent session, such as:
- **Running Django Migrations**: `docker-compose run --rm -e DATABASE_URL=$DATABASE_URL_DIRECT web python manage.py migrate`
- **Running Management Commands**: Many management commands might benefit from a direct connection.
- **Debugging**: Connecting directly to the DB for troubleshooting.

## 4. Deployment and Operations

The `pgbouncer` service is configured to start automatically with `sudo docker compose up`. The application (`web` service) is already set to depend on it.

### Quick Rollback / Bypassing PgBouncer

If you suspect PgBouncer is causing issues and need to bypass it quickly, you can do the following:

1.  **Stop the running services**:
    ```bash
    sudo docker compose down
    ```
2.  **Modify your `.env` file**:
    Comment out the `DATABASE_URL` line and rename `DATABASE_URL_DIRECT` to `DATABASE_URL`.
    ```dotenv
    # DATABASE_URL="postgres://..."
    DATABASE_URL="postgres://your-db-user:your-db-password@db:5432/your-db-name"
    ```
3.  **Restart the services**:
    ```bash
    sudo docker compose up -d
    ```
The application will now connect directly to the database. Remember to also adjust the `depends_on` section in `docker-compose.yml` from `pgbouncer` back to `db` for a complete rollback.

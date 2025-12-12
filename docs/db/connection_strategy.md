# Database Connection Management Strategy

This document outlines our strategy for managing database connections to ensure stability, performance, and scalability.

## 1. Core Components

Our connection management stack consists of three main layers:
1.  **PostgreSQL**: The database server.
2.  **PgBouncer**: A lightweight connection pooler.
3.  **Django Application**: The client application.

## 2. Configuration Parameters and Rationale

The connection limits and timeouts are configured conservatively as a safe starting point. **These values should be tuned based on performance monitoring and load testing in a staging environment.**

### PostgreSQL (`postgres` service)

-   **`max_connections = 100`**
    -   **Rationale**: This is the hard limit of connections the database server will accept. We've set it to a moderate value. Each connection consumes memory, so this number should be based on the server's available RAM. A common formula is to start with a value based on `(Total RAM / 4MB)`. For a server with 4GB RAM, this would be around 1000, but we start lower to be safe. `100` is a very conservative value suitable for small to medium loads.

-   **`statement_timeout = 15s`**
    -   **Rationale**: Aborts any query that runs for more than 15 seconds. This is a crucial guardrail to prevent runaway queries from locking up resources or causing cascading failures.

-   **`idle_in_transaction_session_timeout = 30s`**
    -   **Rationale**: Terminates any session with an open transaction that has been idle for more than 30 seconds. This prevents application bugs (e.g., forgetting to commit a transaction) from holding locks and connections for extended periods.

### PgBouncer (`pgbouncer` service)

-   **`pool_mode = transaction`**
    -   **Rationale**: Connections are assigned for the duration of a single transaction. This is the safest and most efficient mode for Django, which typically uses short-lived transactions (autocommit mode).

-   **`default_pool_size = 20`**
    -   **Rationale**: PgBouncer will maintain up to 20 open connections to the PostgreSQL server per database/user pair. This is our "hot" pool of ready-to-use connections.

-   **`max_client_conn = 80`**
    -   **Rationale**: PgBouncer will accept a maximum of 80 incoming connections from the Django application. This value is intentionally set lower than PostgreSQL's `max_connections` (100). This leaves a **safety margin of 20 connections** for other clients, such as:
        -   Direct connections for running migrations (`DATABASE_URL_DIRECT`).
        -   Database superusers performing maintenance.
        -   Monitoring tools.
    If the application tries to exceed 80 connections, PgBouncer will queue the requests, preventing the database from being overwhelmed.

## 3. Flow of Connections

1.  The Django application (running in multiple containers/processes) opens connections to PgBouncer. It can open up to `80` connections in total.
2.  PgBouncer manages these client connections.
3.  When a Django process runs a query, PgBouncer assigns it a "hot" connection from its pool of `20` server connections.
4.  Once the transaction is complete, the server connection is returned to the pool, ready for another client.
5.  If all `20` server connections are in use, the next client request will be queued by PgBouncer until a connection becomes available.

This setup ensures the database is never overloaded with connection requests, and the application experiences low latency as it's almost always receiving a pre-warmed connection.

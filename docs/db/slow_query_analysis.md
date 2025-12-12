# How to Analyze Slow Queries

This document provides a guide on how to access and analyze PostgreSQL's slow query logs, which have been enabled in our development environment.

## 1. Viewing Slow Query Logs

In our Docker Compose setup, the PostgreSQL container is configured to output its logs to `stdout`. This means you can easily view all logs, including slow query statements, using the following command:

```bash
sudo docker compose logs -f db
```

A "slow query" is defined by the `log_min_duration_statement` parameter, which is currently set to `500ms`. Any query that takes longer than this threshold to execute will be logged.

### Understanding the Log Format

The log line prefix is configured to provide maximum context:
`log_line_prefix='%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '`

This format includes:
- `%t`: Timestamp
- `%p`: Process ID (PID)
- `%l-1`: Log line number within the session
- `%u`: Username
- `%d`: Database name
- `%a`: Application name (if set)
- `%h`: Client host

Example of a slow query log entry:
```
2025-12-12 16:30:00.123 UTC [12345]: [1-1] user=myuser,db=mydb,app=psql,client=172.20.0.1 LOG:  duration: 850.123 ms  statement: SELECT ...
```

## 2. Analyzing Logs with `pgbadger`

For more in-depth analysis, especially with a large volume of logs, using a log analyzer like `pgbadger` is highly recommended. `pgbadger` is a powerful PostgreSQL log analyzer that creates detailed reports from your log files.

### How to use `pgbadger`:

**Step 1: Save the logs to a file**

First, capture the PostgreSQL logs into a file. You can do this by redirecting the output of the `docker compose logs` command:

```bash
sudo docker compose logs db > postgres.log
```
Let this run for a period of time to collect a representative sample of queries.

**Step 2: Run `pgbadger`**

If you don't have `pgbadger` installed locally, you can use its Docker image for convenience. Run the following command from the directory where you saved `postgres.log`:

```bash
docker run --rm -v "$(pwd):/data" -w /data dverite/pgbadger -f stderr -p '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h ' postgres.log -o pgbadger_report.html
```
* `-v "$(pwd):/data"`: Mounts the current directory into the container.
* `-f stderr`: Tells pgbadger to parse logs from stderr (Docker's default).
* `-p '...'`: **Crucially**, this specifies the custom `log_line_prefix` format we use.
* `postgres.log`: The input log file.
* `-o pgbadger_report.html`: The output report file.

**Step 3: View the report**

Open the generated `pgbadger_report.html` in your web browser. It will contain a wealth of information, including:
- Top slow queries.
- Most frequent queries.
- Queries that generate the most temporary files.
- Histograms of query times.
- And much more.

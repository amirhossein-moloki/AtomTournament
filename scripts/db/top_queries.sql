-- top_queries.sql
-- This script helps identify the most resource-intensive queries
-- by leveraging the pg_stat_statements extension.
--
-- How to run:
-- 1. Connect to your PostgreSQL database:
--    psql -U your_user -d your_db
-- 2. Run the script:
--    \i /path/to/this/script/top_queries.sql
--
-- Or run it directly via docker-compose:
-- docker-compose exec db psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -a -f /app/scripts/db/top_queries.sql

-- Reset stats if needed (use with caution)
-- SELECT pg_stat_statements_reset();

-- Top 10 queries by total execution time
-- Queries that, in aggregate, consume the most CPU time. Good candidates for optimization.
SELECT
    (total_exec_time / 1000 / 60) as total_minutes,
    (mean_exec_time) as avg_ms,
    calls,
    query
FROM
    pg_stat_statements
ORDER BY
    total_exec_time DESC
LIMIT 10;

-- Top 10 queries by average execution time
-- Queries that are individually slow. Could indicate missing indexes or inefficient plans.
SELECT
    (mean_exec_time) as avg_ms,
    calls,
    query
FROM
    pg_stat_statements
ORDER BY
    mean_exec_time DESC
LIMIT 10;

-- Top 10 queries by number of calls
-- Frequently executed queries. Even small improvements can have a big impact.
SELECT
    calls,
    (mean_exec_time) as avg_ms,
    query
FROM
    pg_stat_statements
ORDER BY
    calls DESC
LIMIT 10;

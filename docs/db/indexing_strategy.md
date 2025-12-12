# Indexing Strategy and Validation

This document outlines the strategy for adding new indexes to the database and the process for validating their impact.

## Current Index Added (Migration `0009_add_tournament_status_index`)

- **Table:** `tournaments_match`
- **Columns:** `(tournament_id, status)`
- **Type:** Composite B-Tree Index
- **Method:** `CREATE INDEX CONCURRENTLY`

### Justification

A common query pattern identified through static code analysis is fetching matches for a specific tournament, filtered by their status (e.g., `pending_confirmation`, `completed`).

```python
# Example from the codebase (conceptual)
Match.objects.filter(tournament=some_tournament, status='completed')
```

Without an index, this query would require a sequential scan on the `tournaments_match` table, which can be very slow as the table grows. The new composite index on `(tournament_id, status)` allows the database to directly locate the relevant rows, significantly speeding up these lookups.

### Validation Process

**IMPORTANT:** Before applying this migration to a production environment, its effectiveness **must** be validated in a staging environment that has a realistic data distribution.

**Step 1: Get the `EXPLAIN ANALYZE` plan BEFORE the index.**

Connect to the staging database and run an `EXPLAIN ANALYZE` on a typical query.

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM tournaments_match
WHERE tournament_id = <some_existing_tournament_id>
  AND status = 'completed';
```

Note the execution plan. You should see a `Seq Scan` on `tournaments_match` and a high execution time.

**Step 2: Apply the migration.**

Run the Django migration to create the index.

**Step 3: Get the `EXPLAIN ANALYZE` plan AFTER the index.**

Run the exact same query again:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM tournaments_match
WHERE tournament_id = <some_existing_tournament_id>
  AND status = 'completed';
```

The new execution plan should now show an `Index Scan` or `Bitmap Heap Scan` using the `tournaments_match_tourn_id_status_idx`. The execution time and buffer reads should be drastically lower.

### Monitoring Index Usage

After deployment, you can monitor whether the index is being used by the database with the following query. An index with a low `idx_scan` count might be a candidate for removal.

```sql
SELECT
    relname AS table_name,
    indexrelname AS index_name,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM
    pg_stat_user_indexes
WHERE
    indexrelname = 'tournaments_match_tourn_id_status_idx';
```

# Bolt's Performance Journal ⚡

## 2025-05-15 - SQL-level filtering vs In-memory processing
**Learning:** The `/api/summary` endpoint was performing O(N) in-memory filtering and aggregation on multiple entities. Moving this logic to the database using SQL `WHERE` clauses and `GROUP BY` significantly reduces data transfer and CPU usage in the application layer. Using `COALESCE` in SQL effectively replicates Python's multi-field date fallback logic.
**Action:** Always prefer SQL-level filtering and aggregation (`COUNT`, `SUM`, `GROUP BY`) over fetching all records and processing them in Python, especially for dashboard summaries.

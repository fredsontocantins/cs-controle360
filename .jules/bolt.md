## 2026-06-16 - Dashboard Summary Optimization (SQL-level aggregation)
**Learning:** Migrating dashboard summary calculations from O(N) in-memory Python filtering to SQL-level `COUNT` and `GROUP BY` operations yields massive performance gains (~18x-20x speedup). Using `COALESCE(NULLIF(field, ''), ...)` in SQL effectively replicates Python's truthiness-based filtering for date fields.
**Action:** Prioritize SQL-level aggregations for all dashboard and reporting endpoints to maintain constant-time performance as the database grows.

## 2026-05-24 - [SQL-level aggregation vs In-memory Python]
**Learning:** Migrating dashboard summary logic from fetching all records into Python memory to using SQL `COUNT` and `GROUP BY` achieved a ~8.5x speedup (0.106s to 0.012s) for 1000 records. Using `COALESCE` in SQL allows replicating complex Python-level date prioritization logic while keeping the query execution on the database engine.
**Action:** Always prefer SQL-level aggregations for dashboard and reporting endpoints. Avoid calling `list_*` methods that fetch all columns if only counts or grouped totals are needed.

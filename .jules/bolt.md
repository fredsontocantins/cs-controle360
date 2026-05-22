
## 2026-05-22 - SQL-level Date Range Filtering for Dashboard
**Learning:** Python-level filtering with multiple date fields (e.g. `check_date`, `created_at`, `production_date`) can be efficiently replicated in SQL using multiple `OR` conditions. This avoids O(N) memory overhead and is crucial for dashboard summary performance.
**Action:** Use SQL `WHERE (field1 >= ? OR field2 >= ?) AND ...` to filter records at the database level when calculating summary metrics.

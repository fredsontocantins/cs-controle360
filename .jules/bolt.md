## 2026-06-10 - SQL Aggregation speedup
**Learning:** Migrating from O(N) Python-side filtering to O(1)/O(log N) SQL-level aggregation (`COUNT`, `GROUP BY`) yielded a ~12x performance boost (0.194s -> 0.016s) for 10,000 records.
**Action:** Prioritize database-level operations for dashboard summaries and reports. Use `COALESCE` to handle priority-based date filtering at the SQL level.

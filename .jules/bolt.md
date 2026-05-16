## 2026-05-16 - [Dashboard Summary Optimization]
**Learning:** Migrating from O(N) in-memory Python filtering to O(1) database-level SQL aggregations and counts drastically improves performance for dashboard endpoints. Using explicit `GROUP BY` expressions ensures compatibility across SQLite and PostgreSQL.
**Action:** Always prefer SQL-level filtering and counting for dashboard metrics. Avoid `len(list_entities())` when a simple `COUNT(*)` suffices.

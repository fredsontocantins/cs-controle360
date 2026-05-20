## 2026-05-20 - [Optimizing Dashboard Summary with SQL Aggregations]
**Learning:** Moving O(N) in-memory filtering and grouping to the database level (O(1) from app perspective) drastically improves performance as data grows.
**Action:** Always prefer SQL-level `COUNT`, `WHERE`, and `GROUP BY` for dashboard statistics instead of fetching full record lists.

## 2026-05-20 - [Handling Schema Inconsistencies]
**Learning:** The `users` table and `auth_audit_logs` had schema inconsistencies in `backend/database.py` compared to their respective models, causing tests to fail when bootstrapping admin users.
**Action:** Align `CREATE TABLE` statements with the model's `columns` tuple to ensure consistency across the application.

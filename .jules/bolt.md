## 2025-05-11 - Optimization of /api/summary endpoint
**Learning:** Migrating from O(N) in-memory Python filtering and aggregation to O(1) database-level SQL operations (COUNT, GROUP BY) significantly improves API response time, especially as the dataset grows. In this specific case, response time for 10,000 records per entity dropped from ~1.65s to ~0.24s.
**Action:** Always prefer SQL-level aggregations and filtering for dashboard summaries and reports instead of loading full record lists into application memory.

## 2025-05-11 - BaseRepository SQL Compatibility
**Learning:** The `BaseRepository` used a simple `?` to `%s` replacement for PostgreSQL compatibility. While working for basic cases, it's a pattern to watch for if complex literal strings containing `?` are ever used in queries.
**Action:** Be mindful of SQL placeholder conversion logic when supporting multiple database engines.

## 2025-06-13 - SQL-level Aggregation for Dashboard Summary
**Learning:** Migrating from O(N) in-memory Python filtering and grouping to SQL-level `COUNT` and `GROUP BY` operations provides a massive performance boost as the dataset grows. For 5,000 records, the response time dropped from ~245ms to ~24ms (10x speedup).
**Action:** Always prefer SQL aggregations over in-memory Python processing for dashboard statistics and summaries. Ensure `BaseRepository` or specific repositories encapsulate these queries to maintain cross-database compatibility (SQLite/Postgres).

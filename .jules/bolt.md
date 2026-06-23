# Bolt's Performance Journal ⚡

## 2026-06-23 - [SQL-level filtering for Dashboard Summary]
**Learning:** Migrating from O(N) in-memory Python filtering and counting to database-level SQL aggregations provided a significant speedup for the dashboard summary endpoint. Fetching thousands of records just to count them or group them is a major bottleneck. Using `COALESCE` with `NULLIF(field, '')` in SQL chain accurately replicates Python's truthiness-based priority logic for selecting the "primary" date of a record across multiple fields.

**Action:** Always prefer SQL-level aggregations (`COUNT`, `GROUP BY`) over in-memory processing for dashboard stats and reports. Ensure `BaseRepository` supports a `count` method and optional `where` clauses to facilitate this.

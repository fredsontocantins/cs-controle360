## 2025-05-22 - [SQL-level Filtering for Summary]
**Learning:** In-memory filtering of large datasets in Python (O(N)) is a major bottleneck as the database grows. Moving filtering and counting to the database level (SQL WHERE/COUNT) significantly improves performance and reduces memory usage.
**Action:** Use SQL-level filtering and COUNT(*) for dashboard summaries instead of fetching all records and filtering in memory.

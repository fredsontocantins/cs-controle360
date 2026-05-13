## 2025-05-13 - [Dashboard Summary SQL Optimization]
**Learning:** Moving from O(N) in-memory Python filtering/aggregation to database-level SQL operations (`COUNT`, `WHERE`, `GROUP BY`) provides massive performance gains (approx 10-20x speedup for 10k+ records). Using `COALESCE` with `NULLIF` in SQL effectively replicates Python's "find first non-null field" logic for date range filtering.
**Action:** Always prefer SQL-level aggregations and filtering over fetching full datasets and processing them in Python, especially for dashboard/reporting endpoints.

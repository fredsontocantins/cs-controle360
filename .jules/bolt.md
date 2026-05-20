## 2026-04-26 - [Server-side filtering for listing activities and customizations]
**Learning:** In-memory filtering of database results (O(N) in Python) is a common bottleneck as datasets grow. Moving filtering to the SQL layer (WHERE clause) significantly reduces memory usage and data transfer.
**Action:** Always prefer server-side filtering (SQL WHERE clauses) over fetching all records and filtering them in Python, especially for large tables like activities or logs.

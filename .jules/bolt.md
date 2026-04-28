## 2026-04-28 - SQL-level Filtering and Counting
**Learning:** Moving from O(N) in-memory filtering (fetching all records and then filtering in Python) to SQL-level filtering (`WHERE` clauses) and counting (`COUNT(*)`) provides massive performance wins as the dataset grows. It reduces memory usage, CPU time on the application server, and network bandwidth between the DB and the app.

**Action:** Always prefer server-side filtering and counting. Implement core repository methods like `count()` and `list(where, params)` early in a project's lifecycle to avoid building O(N) bottlenecks in analytics/summary endpoints.

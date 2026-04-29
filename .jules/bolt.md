## 2025-05-23 - [SQL-level filtering and counting]
**Learning:** In-memory filtering of large datasets (like dashboard summaries) using Python's `len()` and list comprehensions is a significant performance bottleneck ((N)$). Moving these operations to the database using `COUNT(*)` and `WHERE` clauses reduces database traffic and processing time to (\log N)$ or better.
**Action:** Always prefer server-side SQL filtering and counting for summary endpoints or large datasets.

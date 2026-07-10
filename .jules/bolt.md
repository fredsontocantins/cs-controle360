## 2024-05-24 - [Optimized Dashboard Summary with SQL Aggregation]
**Learning:** In-memory filtering and grouping of large datasets in Python (using list comprehensions and manual loops) creates significant latency as the database grows. Migrating these operations to SQL (COUNT, GROUP BY, COALESCE) reduced response time from ~0.43s to ~0.03s for 10,000 records.
**Action:** Always prefer SQL-level filtering (WHERE) and aggregation (GROUP BY) over fetching full datasets and processing them in Python, especially for dashboard summaries.

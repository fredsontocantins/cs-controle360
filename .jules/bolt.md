# Bolt's Performance Journal ⚡

## 2025-05-09 - SQL-level filtering for dashboard summary
**Learning:** In-memory filtering of large datasets (like 1000+ records) in Python leads to significant O(N) bottlenecks, especially when multiple tables are involved. Moving filtering and aggregation to SQL using `COUNT(*)` and `GROUP BY` provides a massive performance boost (~20x improvement in this case).
**Action:** Always prefer SQL-level filtering and aggregation over loading entire tables and filtering in Python. Use `BaseRepository.count()` and `BaseRepository.list(where=...)` for efficient data retrieval.

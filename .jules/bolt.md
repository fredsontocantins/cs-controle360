## 2025-05-08 - Dashboard Summary Optimization
**Learning:** Pre-fetching and in-memory filtering can significantly speed up dashboard endpoints that aggregate data across multiple cycles. Caching datetime parsing with `lru_cache` provides a major boost when dealing with many date strings.
**Action:** Use pre-fetching and in-memory filtering for summary endpoints. Always cache expensive parsing operations like `parse_cycle_datetime`.

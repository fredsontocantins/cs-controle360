## 2026-05-01 - Dashboard Performance Optimization
**Learning:** SQL-level filtering and counting significantly outperform in-memory Python processing (O(N) vs O(1) or O(log N) with indexes). Using `COALESCE` in SQL allows matching complex multi-field fallback logic while remaining at the database level.
**Action:** Prefer `Repository.count(where=...)` over `len(Repository.list())` for summaries and dashboard metrics.

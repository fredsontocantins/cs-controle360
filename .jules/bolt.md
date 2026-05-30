## 2025-05-15 - SQL-level filtering for dashboard summaries
**Learning:** In-memory Python filtering (e.g., `_filter_cycle_records`) using `datetime.strptime` on every record is a major O(N) bottleneck as the database grows. Moving this logic to SQL using `COUNT(*)` and `WHERE` clauses with parameterized date ranges reduces overhead significantly.
**Action:** Always prefer server-side SQL counting and filtering for dashboard metrics. Ensure `BaseRepository` supports these patterns to avoid repeating manual loops in router logic.

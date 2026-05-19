# Bolt Performance Journal

## 2025-05-19 - Dashboard Summary Optimization
**Learning:** In-memory filtering of large record sets (O(N)) in Python is a major bottleneck as the database grows. Moving this logic to SQL (O(1) or O(log N) with indexes) significantly improves performance.
**Action:** Always prefer SQL-level counts and filters for dashboard/summary endpoints.

**Learning:** When refactoring to SQL, ensure that "Total" metrics remain truly global (unless the business logic explicitly requires otherwise) to avoid UI regressions.
**Action:** Keep global counts separate from cycle-filtered counts in the summary API.

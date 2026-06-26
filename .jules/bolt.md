## 2026-06-26 - Optimized Dashboard Summary
**Learning:** The `/api/summary` endpoint had an O(N) database access pattern where it fetched all records for every report cycle (current, previous, and selected). Memoizing datetime parsing and pre-fetching all records once reduced mean response time by ~28%.
**Action:** Always pre-fetch bulk data before loops and cache expensive computations like `datetime.strptime` if the same strings are processed multiple times.

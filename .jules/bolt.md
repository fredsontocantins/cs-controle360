## 2026-06-01 - Optimizing N+1 query patterns in Dashboard Summaries
**Learning:** Pre-fetching full record sets for entities once at the start of a request and reusing them for multi-period window calculations (cycles) is significantly faster than repeated individual database queries, especially when combined with record-level parsed-datetime caching.
**Action:** Always check for repeated 'list_entity()' calls within loops or nested functions in dashboard/summary logic and refactor to a single pre-fetch pattern.

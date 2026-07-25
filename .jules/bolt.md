# Bolt's Performance Journal

This journal documents critical learnings on performance bottlenecks, optimizations, and codebase-specific patterns in CS-Controle 360.

## 2026-07-25 - [Pre-fetching and Caching Operational Lists in Summary Endpoint]
**Learning:** Repetitive sequential queries to get list and historical records inside loop helpers (such as `build_cycle_summary` execution for previous, current, and selected cycles) trigger an N+1 database call pattern and redundantly re-parse / re-normalize the same rows up to 3-4 times. Pre-fetching and caching full lists once at the start of `/api/summary` dramatically reduces I/O and CPU overhead.
**Action:** Always pre-fetch full collections or datasets when helper loops require multiple subset filters or aggregations within the same API request.

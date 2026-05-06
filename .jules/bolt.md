# Bolt's Journal - Performance Optimizations

## 2026-05-06 - [Date Parsing & N+1 Query in Summary]
**Learning:** The `/api/summary` endpoint suffered from an N+1 query problem where it fetched collections (homologations, customizations, activities, releases) multiple times for each report cycle. Additionally, `parse_cycle_datetime` was a significant CPU bottleneck due to inefficient format trial-and-error and lack of caching.

**Action:**
1. Pre-fetch all entity collections once at the start of the endpoint and use in-memory filtering.
2. Optimize `parse_cycle_datetime` by:
   - Using `@lru_cache` to avoid redundant parsing.
   - Prioritizing `datetime.fromisoformat` which is much faster than `strptime`.
   - Adding a fast-path for already parsed `datetime` objects.

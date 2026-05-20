# Bolt's Performance Journal

## 2026-05-20 - [Dashboard Summary N+1 Query & Datetime Parsing Optimization]
**Learning:** The `/api/summary` endpoint was suffering from N+1 query patterns by calling repository methods and `get_cycle_window` (which also performs DB calls) multiple times within loops. Additionally, `parse_cycle_datetime` was a hotspot due to repeated `strptime` calls on the same date strings.
**Action:** Pre-fetch all entity record sets once at the start of the request. Use a local, optimized `get_window` helper that operates on pre-fetched cycle data. Implement `@lru_cache` for `parse_cycle_datetime` and prioritize `datetime.fromisoformat` for a significant speed boost.

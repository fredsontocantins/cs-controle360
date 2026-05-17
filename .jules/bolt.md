## 2025-05-17 - Dashboard Summary N+1 Query and Datetime Bottlenecks

**Learning:** The `/api/summary` endpoint exhibited an N+1 query pattern where it repeatedly called list functions for different entities (homologations, customizations, etc.) for each report cycle being summarized. Additionally, repeated string-to-datetime parsing in filtering loops added significant CPU overhead.

**Action:** Implement pre-fetching of all entity record sets once at the start of the request and reuse these lists for all summary calculations. Attach a pre-calculated `_dt` datetime field to records to eliminate redundant parsing. Use `@lru_cache` on the core `parse_cycle_datetime` utility to speed up repeated lookups for common timestamp strings.

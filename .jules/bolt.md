## 2026-06-24 - Optimization of /api/summary and parse_cycle_datetime
**Learning:** The `/api/summary` endpoint performance was improved by ~28% through three key techniques:
1. **Record Pre-fetching:** Fetching all history exactly once at the request start to eliminate O(N) database queries.
2. **Datetime Memoization:** Caching parsed `datetime` objects on record dictionaries using a field-specific key (`_dt_{hash(keys)}`) to avoid redundant `strptime` calls during cross-cycle filtering.
3. **ISO-First Parsing:** Optimizing `parse_cycle_datetime` to try `fromisoformat` first, which is significantly faster than the `strptime` loop.
4. **Pre-calculated Windows:** Computing cycle windows from a pre-fetched list instead of re-querying the database for each cycle summary.

**Action:** For dashboard endpoints that aggregate data across multiple time windows, always combine pre-fetching with memoization for parsed data. Prioritize `fromisoformat` for any datetime parsing from known ISO-compatible sources.

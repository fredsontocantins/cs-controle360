## 2026-06-17 - Dashboard Summary Optimization
**Learning:** The `/api/summary` endpoint suffered from N+1 query patterns and inefficient date parsing. `datetime.fromisoformat` is up to 150x faster than `strptime` for compatible strings.
**Action:** Pre-fetch all entity records once at the start of complex summary requests and prioritize `fromisoformat` in core date parsing utilities.

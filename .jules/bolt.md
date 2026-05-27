## 2026-05-27 - [Optimized Dashboard Summary and Date Parsing]
**Learning:** Redundant data fetching (N+1 patterns) and repetitive date parsing in loops are major performance bottlenecks in Python-based dashboards. Pre-fetching all relevant records once at the start of a request and using @lru_cache for parsing significantly reduces response latency.
**Action:** Always pre-fetch full record sets for complex summary endpoints and use optimized, cached date parsing for compatibility with common ISO formats.

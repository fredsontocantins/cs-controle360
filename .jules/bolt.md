## 2026-06-23 - Summary Endpoint Optimization
**Learning:** The `get_summary` endpoint suffered from N+1 query patterns and redundant datetime parsing. Pre-fetching entity lists and caching parsed datetimes on record objects significantly improved performance.
**Action:** Always check for N+1 queries in aggregate endpoints and use transient in-memory caching for expensive operations (like datetime parsing) that are repeated for the same data within a request.

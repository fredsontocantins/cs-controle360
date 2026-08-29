## 2026-08-29 - Pre-fetching operational records in intelligence hub router
**Learning:** `get_consolidated_intelligence` in `backend/routers/reports.py` fetched full lists of `activities` and `releases` multiple times (once for metrics aggregation and again inside `PlaybookGenerator.build_dashboard`). Reusing pre-fetched in-memory lists when `cycle_id` is None eliminates duplicate database queries.
**Action:** Always check if dependent services/generators can accept pre-fetched domain records instead of querying the database independently within the same request handler.

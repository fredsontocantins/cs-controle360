## 2026-08-21 - Reusing pre-fetched lists across sub-modules
**Learning:** Reusing pre-fetched standard lists of activities and releases for the playbook dashboard when `cycle_id` is None eliminates redundant database query operations in `get_consolidated_intelligence`.
**Action:** Always inspect endpoint handlers for duplicate data fetching across sub-components before making separate database query calls.

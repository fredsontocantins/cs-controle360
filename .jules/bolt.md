## 2025-05-15 - [Dashboard Summary Optimization]
**Learning:** Consolidating database fetches for dashboard summaries can yield significant performance gains (approx. 10% in this case) even with small datasets. Reusing local helpers like `_filter_cycle_records` for in-memory filtering is preferred over importing internal model functions (`_within_current_cycle`), ensuring better encapsulation and logic reuse.
**Action:** Always check for redundant `list_...` calls in reporting/dashboard endpoints and consolidate them into pre-fetched variables passed to sub-functions.

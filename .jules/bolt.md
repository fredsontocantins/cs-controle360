## 2025-05-14 - Dashboard Summary N+1 optimization
**Learning:** The `/api/summary` endpoint was calling `list_*` functions multiple times (once per cycle summarized), leading to redundant `SELECT *` queries on large tables. Pre-fetching all records into memory once and filtering them using the internal `_filter_cycle_records` helper significantly reduces database load.
**Action:** Always check if a loop or multiple function calls are repeatedly querying the same dataset and consider pre-fetching.

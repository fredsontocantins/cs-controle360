# Bolt's Performance Journal

## 2026-07-04 - Summary Optimization and Datetime Parsing
**Learning:** The `get_summary` endpoint was suffering from a bottleneck due to redundant database calls and expensive datetime parsing within a loop for multiple report cycles. Specifically, `parse_cycle_datetime` was using a loop of `strptime` calls, which is significantly slower than `datetime.fromisoformat` for ISO-compliant strings. Additionally, re-fetching all records for each cycle was leading to $O(N \times C)$ complexity where $N$ is the number of records and $C$ is the number of cycles.

**Action:**
1. Optimized `parse_cycle_datetime` by attempting `fromisoformat` first.
2. Refactored `get_summary` to pre-fetch records and pre-calculate cycle windows.
3. Implemented a temporary caching mechanism for parsed datetimes on record objects within the filtering loop to avoid repeated parsing of the same record strings for different cycles.
4. Preserved original global totals while utilizing optimized pre-fetched lists.

**Impact:** Mean response time for `/api/summary` with 1000 records reduced from ~200ms to ~41ms (~80% faster).

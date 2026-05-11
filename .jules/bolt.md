## 2026-05-11 - [Summary Endpoint N+1 Queries]
**Learning:** The `/api/summary` endpoint was fetching entire entity lists (activities, homologations, etc.) inside a loop for each report cycle (current, previous, selected). This resulted in redundant database I/O that scaled with the number of cycles requested.
**Action:** Pre-fetch all entities with `include_history=True` once at the start of the request and use in-memory filtering for cycle-specific totals. Ensure that main dashboard counts still apply the correct cycle filtering logic to maintain functional parity.

## 2026-05-11 - [Expensive Date Parsing]
**Learning:** `datetime.strptime` is significantly slower than `datetime.fromisoformat`. In endpoints processing hundreds of records, repeated date parsing becomes a CPU bottleneck.
**Action:** Use `@lru_cache` for date parsing utilities and prioritize `fromisoformat` when standard ISO strings are expected.

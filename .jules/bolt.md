# Bolt's Performance Journal ⚡

## 2026-05-01 - [Pre-fetching and in-memory window lookups for /api/summary]
**Learning:** Multiple sequential database list fetches (e.g., `list_homologacao(include_history=True)`) and window calculations inside report cycle summary loops create severe N+1 query overhead, resulting in 25+ database operations per dashboard load. By pre-fetching lists once and mapping report cycle windows O(1) in memory from the sorted cycles list, we can dramatically improve response times and minimize database connection overhead.
**Action:** Always pre-fetch full collections and pre-calculate sequence boundaries in memory before entering helper loops that build period-specific or categorized summaries.

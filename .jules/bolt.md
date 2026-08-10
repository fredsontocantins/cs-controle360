# Bolt's Performance Journal ⚡

## 2026-08-10 - Pre-fetching and request-scope caching in `/api/summary`
**Learning:** Calling database list endpoints (`list_homologacao`, `list_customizacao`, etc.) inside loops (e.g. over multiple report/execution cycles) results in N+1 style query behavior, dramatically increasing database roundtrips. Request-scope pre-fetching and caching in local variables solves this beautifully.
**Action:** Always verify if database fetches inside inner functions or loops can be pre-fetched once and passed down or reused within request scope to cut down on redundant queries.

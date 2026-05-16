# Bolt's Journal ⚡

## 2026-05-16 - Dashboard Summary N+1 Query Optimization
**Learning:** The `/api/summary` endpoint exhibited an N+1 query pattern where it fetched historical records for multiple entities (homologations, customizations, etc.) for each report cycle being summarized. This resulted in redundant database calls that grew linearly with the number of closed cycles. Additionally, date parsing using `strptime` was a significant overhead during in-memory filtering.
**Action:** Implemented pre-fetching of all entity records once at the start of the request and replaced repository calls with in-memory filtering. Optimized date parsing by prioritizing `datetime.fromisoformat` and applying `@lru_cache` to `parse_cycle_datetime`. In-memory filtering must be careful to replicate original repository logic (e.g., normalization of person names) to avoid functional regressions.

## 2026-05-16 - FastAPI TestClient Startup Events
**Learning:** In this codebase, the database tables are initialized during the FastAPI `startup` event. Simply creating a `TestClient(app)` instance does not trigger these events; the client must be used as a context manager (`with TestClient(app) as client:`) to ensure `ensure_tables()` and other bootstrap logic runs.
**Action:** Always use `with TestClient(app)` in benchmark and test scripts to ensure a consistent and initialized environment.

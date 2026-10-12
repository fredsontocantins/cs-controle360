## 2026-10-12 - Reusing Pre-fetched Data in Consolidated Intelligence Hub Endpoint

**Learning:** `get_consolidated_intelligence` in `backend/routers/reports.py` invoked `list_documents()`, `atividade.list_atividade()`, and `release.list_release()` multiple times in a single request across sub-services (`refresh_application_context`, `build_cycle_audit`, and `PlaybookGenerator`). Pre-fetching documents once and reusing active lists when `cycle_id` is None eliminated 3 redundant database queries per request, reducing mean endpoint latency by ~25% (from ~7.10ms to ~5.36ms).

**Action:** When designing or updating composite aggregator endpoints (such as dashboard or intelligence hubs), always inspect sub-service parameters to pass pre-fetched collections rather than allowing each sub-service to issue its own identical DB queries.

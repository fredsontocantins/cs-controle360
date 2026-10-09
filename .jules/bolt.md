# Bolt ⚡ Performance Journal

## 2026-10-09 - Avoid Redundant Database Reads in Composite Report Endpoints
**Learning:** Composite intelligence endpoints like `/api/reports/intelligence` often construct response payloads from multiple service modules (e.g. PDF Intelligence, Playbook Dashboard, Cross-Module Metrics). Sub-service calls like `refresh_application_context` and `build_cycle_audit` can independently query the same underlying tables (e.g., `pdf_documents`, `activities`, `releases`). Allowing optional pre-fetched lists (`docs`, `activities`, `releases`) to be passed to service methods eliminates redundant database roundtrips.
**Action:** Always inspect composite route handlers for repeated calls to list-fetching functions (`list_documents`, `list_atividade`, `list_release`) and pass shared pre-fetched collections to downstream helper methods.

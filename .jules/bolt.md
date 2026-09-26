## 2026-09-26 - Consolidated Intelligence Hub Database Pre-fetching Optimization
**Learning:** Calling sub-service methods (`refresh_application_context` and `build_cycle_audit`) without passing shared state causes redundant `list_documents()` database queries. Reusing pre-fetched activity/release lists when `cycle_id` is None avoids re-querying `list_atividade()` and `list_release()` in cross-module metrics calculation.
**Action:** Always accept optional pre-fetched lists (`docs=...`) in service context builders to allow upper-level router handlers to fetch dataset once and pass it down.

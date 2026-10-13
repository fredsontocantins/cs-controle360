# Bolt Journal ⚡

## 2026-10-13 - Batch Pre-fetching in Intelligence Consolidation
**Learning:** Calling `list_documents()` multiple times across sub-services in `/reports/intelligence` added redundant database query roundtrips and JSON decoding operations. Passing pre-fetched records into `refresh_application_context` and `build_cycle_audit` reduced execution time by ~28%.
**Action:** Always pre-fetch and pass shared domain entities into sub-service methods when building consolidated dashboards or intelligence hubs.

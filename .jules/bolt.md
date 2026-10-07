## 2026-10-07 - Pre-fetching and reusing operational lists in consolidated endpoints

**Learning:** The `get_consolidated_intelligence` endpoint in `backend/routers/reports.py` was making redundant database queries (`list_atividade` and `list_release`) when `cycle_id` was `None`. By pre-fetching `all_atividades` and `all_releases` once for cross-module metrics and reusing them for the playbook dashboard calculations, we eliminated multiple O(N) database queries per request.

**Action:** When building aggregated or consolidated endpoints that combine metrics from multiple modules, pre-fetch full operational entity lists at the beginning of the handler and pass the cached collections to child generators instead of letting sub-services perform duplicate full table scans.

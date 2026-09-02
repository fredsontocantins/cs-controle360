## 2026-09-02 - Single-Fetch Pre-calculation for Dashboard Cycles
**Learning:** Calling `list_homologacao(include_history=True)` and related repository list functions inside loop functions like `build_cycle_summary` re-executes full database table scans and deserialization for every cycle evaluated (up to 12 unnecessary DB queries per `/api/summary` request).
**Action:** Pre-fetch full operational history lists once at the start of composite summary handlers and pass pre-fetched data to calculation helpers.

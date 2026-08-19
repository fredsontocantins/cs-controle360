## 2026-08-19 - Operational List Pre-fetching in Cycle Aggregations
**Learning:** Repeated calls to `list_homologacao(include_history=True)`, `list_customizacao(include_history=True)`, `list_atividade(include_history=True)`, and `list_release(include_history=True)` inside cycle summary loops (`build_cycle_summary` and `_build_management_report`) triggered up to 12-20 redundant database queries and O(N) dict deserialization passes per API request.
**Action:** Pre-fetch operational history lists once at the handler/method boundary and pass the in-memory lists to sub-routines.

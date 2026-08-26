## 2026-04-28 - Avoid Redundant Operational List Queries in Reports Intelligence Hub
**Learning:** The consolidated intelligence endpoint pre-fetches operational records (`all_atividades` and `all_releases`) for cross-module metrics. When `cycle_id` is None, re-querying `atividade.list_atividade` and `release_model.list_release` for playbook generation creates duplicate O(N) database queries.
**Action:** Always reuse pre-fetched operational datasets across internal service/generator steps when filtering conditions (e.g. `cycle_id is None`) permit.

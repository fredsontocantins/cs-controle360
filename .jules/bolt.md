## 2026-09-22 - Reusing Pre-Fetched Records in Reports Intelligence
**Learning:** In endpoints that aggregate cross-module data alongside playbook metrics, pre-fetching operational records (`all_atividades`, `all_releases`) early in the handler and passing them down when `cycle_id` is `None` eliminates redundant secondary database queries without breaking history-aware queries.
**Action:** Always check if broad list methods like `list_atividade()` or `list_release()` are called multiple times in a single request pipeline and reuse pre-fetched record sets.

## 2026-10-03 - Reuse operational queries in consolidated endpoints
**Learning:** In consolidated endpoints like `/api/reports/intelligence`, sub-service builders (e.g., Playbook dashboard and Cross-module metrics) require full lists of operational records. Fetching `list_atividade()` and `list_release()` separately in each step when `cycle_id` is `None` causes duplicate database queries and record parsing.
**Action:** Pre-fetch operational lists once at the start of the handler and pass them down to downstream services to minimize redundant DB calls and object creation overhead.

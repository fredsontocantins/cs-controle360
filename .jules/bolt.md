## 2026-10-05 - Avoid redundant operational list fetches in intelligence endpoints
**Learning:** In multi-section backend endpoints (like `/reports/intelligence`), separate generator components (e.g. playbook dashboard vs. cross-module metrics) may independently call list functions (`list_atividade`, `list_release`) for default views, leading to duplicate database queries when `cycle_id` is None.
**Action:** Pre-fetch operational lists once at the start of the endpoint function and pass them to downstream services/generators to ensure single-pass DB access.

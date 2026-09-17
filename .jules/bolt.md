## 2026-09-17 - Pre-fetching operational records for cycle summary calculations

**Learning:** Calculating cycle summaries across current and previous report cycles in `ReportGenerator._build_management_report` and `app.get_summary` previously triggered repeated calls to `list_homologacao(include_history=True)`, `list_customizacao(include_history=True)`, `list_atividade(include_history=True)`, and `list_release(include_history=True)`. Each call executed a full database `SELECT *` query, resulting in up to 12-20 redundant database queries per API request. Pre-fetching the operational records once and reusing the lists across cycle calculations eliminates redundant I/O while preserving exact data parity.

**Action:** Always pre-fetch and pass in-memory entity lists when evaluating multi-cycle window filters or summaries rather than calling repository `list_*` functions inside cycle iteration loops.

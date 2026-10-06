# Bolt's Performance Journal ⚡

## 2026-10-06 - Pre-fetching Operational Lists for Cycle Summary Aggregations
**Learning:** `ReportGenerator._build_management_report` was re-invoking `list_homologacao(include_history=True)`, `list_customizacao(include_history=True)`, `list_atividade(include_history=True)`, and `list_release(include_history=True)` up to 8 times inside loop helpers for `current_cycle_summary` and `previous_cycle_summary`. Pre-fetching operational history lists once at the start of report generation eliminates up to 8 redundant database queries per request.
**Action:** Always inspect helper functions called inside report builders or loops to ensure they do not re-query database models when data is already available or can be fetched once in the outer scope.

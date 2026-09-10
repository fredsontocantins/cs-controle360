## 2026-03-30 - Pre-fetching Operational Records for Report Calculations
**Learning:** Calling `list_homologacao()`, `list_customizacao()`, `list_atividade()`, and `list_release()` inside loop evaluations or multi-stage calculations creates severe database round-trip overhead. Pre-fetching operational records once at the start of report generation and reusing them reduces database queries from >10 down to 4 per report call.
**Action:** Always pre-fetch and pass operational lists when generating multi-section reports or consolidated intelligence responses.

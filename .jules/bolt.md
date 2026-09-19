## 2026-09-19 - Operational List Pre-fetching in Report Generation
**Learning:** Calling `list_homologacao`, `list_customizacao`, `list_atividade`, and `list_release` inside sub-calculation loops (such as current and previous cycle window summaries) causes redundant database roundtrips (up to 8 duplicate queries per report).
**Action:** Pre-fetch operational lists once at the start of report aggregation methods and reuse the in-memory records across all cycle window count calculations.

## 2026-09-30 - Reuse Operational Records Pre-fetching in Report Generator
**Learning:** Calling `list_homologacao`, `list_customizacao`, `list_atividade`, and `list_release` inside repeated cycle count evaluation functions in `ReportGenerator._build_management_report` creates up to 8 unnecessary database roundtrips per report request. Pre-fetching all records once at the start of report generation avoids O(N) database queries during cycle window filtering.
**Action:** Always pre-fetch and pass operational lists into cycle window evaluation functions when building complex aggregated reports.

## 2026-09-12 - Pre-fetching Operational Records for Report Generation

**Learning:** The `ReportGenerator._build_management_report` method previously called `list_homologacao`, `list_customizacao`, `list_atividade`, and `list_release` repeatedly inside cycle window count loops, executing up to 8 duplicate full-table database queries per report request. Pre-fetching these lists once at the start of report generation eliminates redundant I/O without altering response structures.

**Action:** Always inspect report and summary builders for loop-internal or multi-pass database fetches, pre-fetching operational record sets once when scope filters permit.

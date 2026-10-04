## 2026-10-04 - Pre-fetching operational records in report generation and intelligence endpoints

**Learning:** In report generation (`ReportGenerator._build_management_report`) and consolidated intelligence (`get_consolidated_intelligence`), operational records (`activities`, `releases`, `homologacoes`, `customizacoes`) were being re-queried from SQLite/Postgres up to 8 times within a single request context. Re-using pre-fetched lists when `cycle_id` is None eliminates redundant DB connections, table scans, and object mappings.

**Action:** Always pre-fetch and pass in-memory lists across sub-calculations in report generators instead of invoking list functions inside loops or helper methods.

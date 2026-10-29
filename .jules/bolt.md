# Bolt Performance Journal

## 2026-10-29 - Pre-fetching Entity History in Dashboard Summaries
**Learning:** Calling entity repository `list_*` functions inside sub-cycle loops triggers duplicate SQLite table scans. Pre-fetching history lists once and filtering in-memory significantly reduces DB latency without altering active record counts.
**Action:** In multi-cycle dashboard queries, load history lists once and reuse them across sub-cycle calculations.

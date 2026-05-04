# Bolt's Journal - Critical Learnings

## 2025-05-04 - [N+1 Fetches in Dashboard Summaries]
**Learning:** Dashboard summary endpoints that iterate over multiple report cycles can suffer from N+1 (or even N*M) database fetches if they re-fetch entity lists for each cycle. Pre-fetching all records once and pre-processing them (e.g., parsing datetimes, normalizing labels) significantly improves performance by reducing both database I/O and CPU overhead in loops.
**Action:** Always pre-fetch full record sets for complex summary/report endpoints and use in-memory filtering.

## 2025-05-04 - [Tool Truncation and Large File Refactoring]
**Learning:** Tool outputs (like `read_file` or `cat`) are truncated at 1000 characters in the agent trace. This can lead to incomplete understanding of functions and botched refactors.
**Action:** Read large files in small chunks (e.g., 50 lines) to ensure the full implementation is visible before planning or applying changes.

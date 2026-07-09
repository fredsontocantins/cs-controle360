## 2026-07-09 - get_summary endpoint optimization
**Learning:** The `get_summary` endpoint was a performance bottleneck due to redundant database queries and repeated datetime/name parsing within cycle loops. Pre-fetching all records and caching parsed values (names, datetimes) in-memory significantly reduces response time. However, mutating shared record objects with internal cache keys (e.g., `_dt_*`) can leak implementation details to the API response if not properly cleaned up.
**Action:** Always implement a `cleanup` step when using in-memory caching/augmentation of data dictionaries before returning them in an API response to ensure implementation details are not exposed.

## 2026-07-09 - Database Schema and Repository Alignment
**Learning:** In this codebase, the SQLite schema in `database.py` and the `columns` definition in the repository models must be perfectly aligned. Adding new columns to the repository without a corresponding migration in `database.py` causes `sqlite3.OperationalError` during standard operations like admin bootstrapping.
**Action:** Avoid scope creep by adding unnecessary database columns. If schema changes are required, ensure they are also applied to the `ensure_tables` logic in `database.py`.

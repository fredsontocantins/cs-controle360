## 2026-08-22 - SQLite Introspection Caching for Insert Operations
**Learning:** Performing dynamic SQLite schema introspection (`PRAGMA table_info`) on every `insert` call adds SQL query overhead to all database write operations.
**Action:** Use a module-level `_TABLE_COLUMNS_CACHE` dictionary to cache existing table columns per table name during SQLite insertions, running `PRAGMA table_info` at most once per table.

# Bolt's Performance Journal

## 2026-07-16 - Summary Endpoint Batching & Pre-parsing
**Learning:** The `get_summary` endpoint previously performed multiple redundant database queries and repeated string-to-datetime parsing for the same records across different reporting cycles. By fetching global lists once and pre-parsing metadata (dates, names) into the record dictionaries, we significantly reduced the CPU and I/O overhead.

**Action:** For dashboard-like endpoints that aggregate data across multiple buckets (e.g., cycles), always batch fetch global data and pre-process metadata before bucket allocation. Use `@lru_cache` for expensive formatting or parsing logic that cannot be batched.

## 2026-07-16 - SQLite Schema Strictness in Repositories
**Learning:** SQLite repositories using a generic `BaseRepository` with fixed `columns` definitions are extremely sensitive to schema mismatches. Passing a dictionary with extra keys (like service-layer abstractions) to `Repository.insert` or `Repository.update` triggers `sqlite3.OperationalError: table X has no column named Y`.

**Action:** Always ensure repository `columns` tuples strictly match the physical SQLite schema. Implement explicit mapping/filtering helpers in the model layer to strip or map service-layer fields before they reach the repository's generic CRUD methods.

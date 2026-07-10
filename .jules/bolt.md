## 2026-07-10 - [Schema Alignment vs Performance]
**Learning:** Modifying repository `columns` tuples to include new fields or remove existing ones without corresponding SQL schema migrations causes `sqlite3.OperationalError` and blocks the application and tests.
**Action:** When optimizing, keep persisted model metadata strictly aligned with the database schema. Implement performance gains (like pre-parsing or caching) as transient, in-memory transformations in the service or router layer using internal keys (e.g., prefixing with `_`).

## 2026-05-26 - [SQL Aggregations vs In-Memory Processing]
**Learning:** Moving data aggregation (COUNT, GROUP BY) and filtering (COALESCE date prioritization) from Python memory to SQL results in a ~10-20x speedup for dashboard endpoints as the dataset grows beyond a few hundred records.
**Action:** Always prefer SQL-level aggregations for summary endpoints. Use COALESCE in SQL to replicate multi-field prioritization logic previously handled in Python helpers.

## 2026-05-26 - [Schema Alignment for Repositories]
**Learning:** Repositories inheriting from a generic BaseRepository require exact schema alignment in the database creation logic. Discrepancies between TABLE_USER or TABLE_AUTH_AUDIT and their respective Repository.columns result in runtime insertion errors.
**Action:** Verify that SQLite/Postgres CREATE TABLE statements exactly match the Repository class column definitions and Pydantic schemas.

# Bolt's Journal - Critical Learnings

## 2026-08-31 - Consolidated Database Operations for API Summary Endpoints
**Learning:** In Next.js App Router API routes querying Supabase/PostgreSQL, making multiple separate `.select()` queries to the same table (e.g. for exact count, status filtering, owner aggregation) causes unnecessary database network round-trips and redundant table scans.
**Action:** Consolidate multiple queries on the same table into a single projection query with `{ count: "exact" }` to fetch counts and required fields in a single query execution.

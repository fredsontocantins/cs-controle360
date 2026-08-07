# Bolt's Journal - Performance Learnings

## 2026-04-28 - Next.js Supabase API Query Redundancy
**Learning:** In the `app/api/summary` Next.js route handler, querying Supabase for different properties of the same entity/table (`activities`) separately results in multiple network roundtrips and full table scans. Combining multiple `.select()` statements on the same table into a single projection query (e.g., `.select("status, owner")`) and aggregating counts in memory reduces the database query count and query latency significantly.
**Action:** Always inspect Next.js or other backend API handlers that pull various aggregations/counts of the same table. Prefetch the required columns in a single projection request and aggregate in memory to conserve DB connection pool limits and minimize API response times.

## 2026-04-28 - Next.js 16/15 Command Parsing Edge Case
**Learning:** In Next.js 16/15 projects without pre-configured eslint setups, running `next lint` is parsed by the Next CLI as running the default development command with a directory parameter called `lint`. This results in the confusing error: `Invalid project directory provided, no such directory: /app/lint`.
**Action:** Prior to running linting on Next.js 16/15 codebases, verify if eslint is actually installed and configured, and run it directly or via ESLint CLI instead of relying blindly on `next lint`.

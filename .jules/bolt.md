# Bolt's Journal - Critical Learnings

## 2025-08-08 - Next.js Dashboard API Query Merging
**Learning:** In Next.js App Router, running separate query operations on the same Supabase table (such as fetching head count, status fields, and owner fields) results in sequential blocking roundtrips if done outside a single unified query. Merging these into a single projection select query (`status, owner`) executed concurrently inside a `Promise.all` reduces network latency, database connection load, and removes redundant serial roundtrips entirely.
**Action:** Always project required attributes under a single unified database query when requesting multiple slices of the same collection, and process/aggregate the data in-memory rather than issuing multiple queries.

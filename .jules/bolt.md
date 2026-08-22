## 2025-05-18 - Single-Pass Projection Queries for Related Aggregations in Next.js API Routes

**Learning:** Requesting full counts and specific projection columns (e.g. `status, owner`) sequentially across multiple queries against the same database table creates unnecessary query waterfalls and network roundtrips.

**Action:** Whenever an endpoint requires both table item counts and grouping/aggregation on specific fields (e.g., `activities`), merge them into a single projection query (`select("status, owner", { count: "exact" })`) inside `Promise.all`. This reduces total DB roundtrips from multi-phase sequential requests down to a single parallel batch and enables single-pass O(N) memory processing.

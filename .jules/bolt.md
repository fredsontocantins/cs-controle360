## 2026-04-28 - Consolidating Multi-Query Aggregations in Next.js Supabase Route Handlers

**Learning:** When fetching metrics across multiple entities in Supabase/PostgreSQL (such as dashboard summaries), fetching head count and field projections (e.g. `status, owner`) in a single query (`supabase.from("activities").select("status, owner", { count: "exact" })`) inside `Promise.all` eliminates duplicate table roundtrips and sequential waterfalls.

**Action:** Whenever building summary endpoints with Supabase, merge exact count requests and field aggregations for the same table into a single projection call instead of making separate `head: true` count queries followed by field-specific `SELECT` queries.

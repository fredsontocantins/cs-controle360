# Bolt's Journal ⚡

## 2026-05-23 - [Optimization of /api/summary]
**Learning:** The dashboard summary endpoint was suffering from a massive N+1 query problem because it was re-fetching every entity (homologations, customizations, activities, releases) for every report cycle being summarized (previous, current, and selected). Additionally, date parsing was a major bottleneck in the filtering loop.
**Action:** Pre-fetch all entities once at the start of the request with `include_history=True`. Pre-calculate expensive values like `datetime` objects and normalized labels once. Use `@lru_cache` for the date parser and prioritize `datetime.fromisoformat` as it's significantly faster than `strptime`.

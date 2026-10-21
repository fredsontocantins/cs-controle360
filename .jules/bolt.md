## 2026-10-21 - Single-pass Group Aggregation for Playbook Intelligence & Pre-fetched Batch Lookup

**Learning:** `PlaybookGenerator.generate_from_errors` previously grouped activities by theme and then called `_series_frequency` which iterated over all activities a second time to execute keyword matching on string concatenation for every item. Computing `max_freq` directly from `grouped.values()` reduced execution time by ~50% (~12.75ms to ~6.43ms for 2000 items). Furthermore, batch endpoints like `/generate/errors` called `list_playbooks()` inside generation loops, which was optimized by pre-fetching a source-key map once before iteration.

**Action:** Avoid re-scanning datasets for frequency metrics when items are already partitioned into grouped data structures. Always pre-fetch existing records into a dictionary map before batch loop operations to prevent redundant N+1 database queries.

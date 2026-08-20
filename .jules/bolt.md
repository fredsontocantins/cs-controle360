# Bolt's Performance Journal - Critical Learnings

## 2026-08-20 - Single-Pass Aggregation over Operational Records
**Learning:** Functions like `PlaybookGenerator.generate_from_errors` previously performed multiple passes over operational activity records—the first pass to group by theme and subsequent passes inside helpers like `_series_frequency` to build frequency distributions and calculate max frequencies. Each pass performed string joins and regex theme classifications on the same data.
**Action:** Always derive frequency metrics directly from the initial grouping data structure (`grouped.values()`) in a single pass to eliminate redundant iterations and string matching overhead.

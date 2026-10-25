## 2026-10-25 - Direct dictionary count extraction avoids redundant O(N) re-scans in generator loops

**Learning:** `PlaybookGenerator.generate_from_errors` grouped items into a `grouped` dict by theme, but then called `_series_frequency(activities)` which re-scanned the entire `activities` list and executed `_detect_theme` string/keyword matching a second time just to compute `max_freq`. Computing `max_freq = max((len(v) for v in grouped.values()), default=1)` directly from the pre-grouped dictionary reduced execution time by ~50% (from ~33.2ms to ~17.1ms for 2,000 records).

**Action:** Whenever operational data is already grouped or aggregated in memory during generator processing, always calculate global stats (such as max frequency or totals) directly from the aggregated dictionary instead of calling helper functions that iterate over the raw collection again.

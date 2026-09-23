## 2026-04-28 - PlaybookGenerator Multi-pass and Keyword Allocation Overhead
**Learning:** `PlaybookGenerator.generate_from_errors` performed multiple passes over activities lists and re-allocated theme keyword iterables and string lists during theme detection. Precomputing tuple-based keyword structures class-wide and computing max frequency in a single grouping pass reduces execution time by ~75%.
**Action:** Always pre-allocate static theme/keyword tuples at class level and avoid redundant list `.join()` string operations inside tight data grouping loops.

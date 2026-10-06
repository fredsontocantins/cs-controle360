# Bolt's Journal - Critical Learnings

## 2026-03-30 - ReportGenerator string datetime parsing & theme analysis
**Learning:** `ReportGenerator._parse_datetime` executes multiple `strptime` attempts on identical string representations across report iterations. Wrapping internal parsing with `@lru_cache(maxsize=4096)` achieves a >50x speedup for repeated date strings. Additionally, pre-extracting ticket details once in `_analyze_themes` eliminates O(N x M) string concatenations across theme categories.
**Action:** Always pre-extract string fields into a single tuple before multi-pass category searching in report generation loops, and use `@lru_cache` for pure datetime string parsing functions.

## 2026-08-16 - LRU Cache for Datetime Parsing in Report Generation
**Learning:** String datetime parsing via strptime in loop-heavy services like `ReportGenerator._parse_datetime` introduces significant CPU overhead (over 1.3 seconds per 50,000 parses).
**Action:** Use a module-level `@lru_cache(maxsize=4096)` wrapper around datetime parsing to achieve ~98% speedup on repeated date format strings.

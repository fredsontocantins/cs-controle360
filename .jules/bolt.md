## 2026-05-22 - Date Parsing Bottleneck
**Learning:** `datetime.strptime` is significantly slower than `datetime.fromisoformat` for ISO-compliant strings. In loops with thousands of records, this becomes a major bottleneck. Caching with `@lru_cache` further improves performance when the same date strings are encountered repeatedly.
**Action:** Always prioritize `fromisoformat` and use caching for repeated date parsing in performance-critical paths.

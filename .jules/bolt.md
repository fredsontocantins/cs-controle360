## 2026-07-03 - Optimize Date Parsing
**Learning:** Using `datetime.strptime` in a loop for multiple formats is significantly slower than `datetime.fromisoformat`. In this codebase, `parse_cycle_datetime` was a bottleneck during record filtering because it attempted multiple `strptime` formats before falling back to `fromisoformat`.
**Action:** Always prioritize `datetime.fromisoformat` for ISO-compliant strings and use it as the first attempt in multi-format parsing utilities to avoid the overhead of `strptime`'s format string parsing and repeated failures.

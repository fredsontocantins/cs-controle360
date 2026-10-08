## 2026-03-31 - Single-pass theme grouping and precomputed tuples in PlaybookGenerator
**Learning:** Re-invoking theme detection functions across multiple passes over thousands of items causes significant CPU bottlenecking during playbook generation. Precomputing tuple keyword constants (`_THEME_KEYWORDS_TUPLES`) and grouping items in a single pass cuts execution time by ~75%.
**Action:** Always check for multi-pass iterations over large lists when classifying/grouping items by text theme, and consolidate classifications into a single dictionary grouping pass.

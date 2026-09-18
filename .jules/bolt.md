# Bolt's Journal - Critical Learnings

## 2025-05-18 - Single-Pass Theme Detection & Tuple Keyword Matching in Playbook Generation
**Learning:** Performing multiple list concatenations (`" ".join([...])`) and multi-pass dictionary/`items()` loops during theme classification for operational records creates significant overhead when processing thousands of items. Pre-compiling tuple pairs (`_THEME_KEYWORDS_TUPLES`) and single-passing activity grouping + frequency counting yields a ~49% speedup.
**Action:** When grouping or classifying records by keywords, pre-compile keyword tuples at class level and accumulate frequencies in a single pass over data rather than re-scanning in helper methods.

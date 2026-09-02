## 2026-04-28 - Single-pass grouping and tuple scanning in PlaybookGenerator
**Learning:** `PlaybookGenerator.generate_from_errors` previously executed two full passes over activities and re-concatenated string attributes on each iteration while re-evaluating theme keywords. Re-evaluating `self.THEME_KEYWORDS` lists generated temporary generator expressions.
**Action:** Pre-compute theme keywords into tuple constants (`_THEME_KEYWORDS_TUPLES`) and perform theme grouping in a single pass over activities.

## 2025-05-18 - Single-Pass Theme Classification in Playbook Generation

**Learning:** `PlaybookGenerator.generate_from_errors` previously executed two passes over all activities: one to group items into themes via `_detect_theme` and a second redundant pass in `_series_frequency` to count themes. Furthermore, `_detect_theme` repeatedly iterated over topic keywords stored as `List[str]`.

**Action:** Pre-compute topic keyword tuples (`_THEME_KEYWORDS_TUPLES`) once on the class level and calculate max frequencies directly from the grouped dict lengths (`max((len(v) for v in grouped.values()), default=1)`), avoiding duplicate iterations and list allocations per item.

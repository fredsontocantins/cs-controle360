# Bolt's Journal - Performance Insights & Learnings

## 2026-09-05 - Avoid Redundant `lower()` Calls on Large Document Text
**Learning:** In text analysis methods like `analyze_pdf`, calling `text.lower()` repeatedly inside nested loops over large strings (e.g., extracted PDF text across multiple topic keywords and section markers) causes quadratic overhead ($O(N \cdot M)$).
**Action:** Pre-compute `text_lower = text.lower()` once at method entry and reuse it for all string comparisons, regex matches, and keyword checks.

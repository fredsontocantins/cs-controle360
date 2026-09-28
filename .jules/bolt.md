# Bolt's Journal

## 2026-03-31 - PDF Text Lowercasing Optimization
**Learning:** Calling `text.lower()` repeatedly inside nested keyword matching loops during PDF text analysis creates massive string allocation overhead (~8x slowdown).
**Action:** Always pre-compute a single `text_lower = text.lower()` string variable before looping over keyword sets or running regex matches on extracted text.

# Bolt's Performance Journal

## 2026-05-18 - Pre-extracting string operations in theme analysis loops
**Learning:** In string-heavy text classification routines (like `ReportGenerator._analyze_themes`), performing string joining and `.lower()` formatting inside inner loops across themes ($K$) and tickets ($T$) causes $O(K \times T)$ redundant string allocations. Pre-extracting search fields in a single $O(T)$ pass and pre-computing lowercased keyword tuples significantly cuts runtime.
**Action:** When searching or matching keywords over collections of dictionaries/objects, pre-process search representations into tuples in a single pass prior to nested evaluation loops.

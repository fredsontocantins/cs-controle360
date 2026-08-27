## 2026-08-27 - PDF Intelligence String Lowercased Loop Optimization

**Learning:** Calling `text.lower()` inside repeated keyword search loops on document text strings (e.g., 200KB PDF content) recreates lowercased string copies on every iteration, causing significant CPU and memory overhead (~246ms per run).
**Action:** Pre-compute `text_lower = text.lower()` once per document and use pre-compiled module-level regex objects for extraction.

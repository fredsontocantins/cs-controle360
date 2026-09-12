# Bolt's Performance Journal

## 2025-05-18 - Pre-compute text lowercasing in PDFIntelligenceService
**Learning:** Calling `text.lower()` inside nested loops for keyword and section matching on large PDF documents causes redundant string allocations and high CPU overhead.
**Action:** Always pre-compute `text_lower = text.lower()` once before performing multi-keyword or regex scans on long text payloads.

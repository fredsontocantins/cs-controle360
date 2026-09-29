## 2026-09-29 - Single-pass text lowercasing in PDF Analysis

**Learning:** `PDFIntelligenceService.analyze_pdf` was lowercasing large PDF text strings repeatedly inside topic and section keyword detection loops (~100+ times per document), creating heavy string allocation and CPU overhead on large documents.

**Action:** Precompute `text_lower = text.lower()` once before topic and section keyword loops to avoid redundant lowercasing ops on large document bodies.

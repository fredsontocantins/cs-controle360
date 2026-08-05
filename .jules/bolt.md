# Bolt's Journal - CS-Controle 360 Performance

## 2026-08-05 - Avoid Redundant String Lowercasing inside Nested Loops
**Learning:** In `PDFIntelligenceService.analyze_pdf`, we iterate over multiple topics and section keywords, performing membership checks (`k in text.lower()`). Since `text` can be very large (containing the full text of parsed PDF documents), repeatedly converting it to lowercase inside these loops causes excessive CPU usage, garbage collection overhead, and slow API response times.
**Action:** Always pre-compute lowercase or normalized versions of large strings (`text_lower = text.lower()`) before entering loops or performing multiple keyword lookups on the same string content.

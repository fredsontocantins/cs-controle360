## 2025-05-18 - Avoid repeated text.lower() conversions in multi-pass PDF string analysis
**Learning:** Performing `text.lower()` inside keyword iteration loops on large PDF extracted text strings introduces significant compute and memory allocation overhead (~35-47% slowdown).
**Action:** Pre-compute `text_lower = text.lower()` once before searching keyword dictionaries, topic maps, and regex patterns on document text.

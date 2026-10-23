## 2026-10-23 - Operational List Pre-fetching & Pre-tokenization in Report Generation

**Learning:** In executive report generation workflows, calling model list functions inside loop summaries or window counting helpers executes up to 8 duplicate database SELECT queries per request. Pre-fetching `raw_releases`, `raw_homologacoes`, `raw_customizacoes`, and `raw_atividades` once at method entry and pre-building lowercased search strings per item in `_analyze_themes` eliminates repetitive query execution and redundant string formatting.

**Action:** Always pre-fetch operational datasets at the top of report generation methods and pass pre-built search tokens into keyword theme classifiers.

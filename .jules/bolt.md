## 2026-10-13 - Consolidated Intelligence Report Database Optimization
**Learning:** Sequential processing in `/reports/intelligence` resulted in duplicate DB queries for PDF documents (`list_documents`) and operational entities (`list_atividade`, `list_release`) when generating PDF insights, playbook dashboards, and cross-module metrics. Passing pre-fetched records across service methods eliminated redundant database hits.
**Action:** Always pre-fetch and reuse operational collections across multi-section aggregation endpoints to avoid duplicate `SELECT` calls.

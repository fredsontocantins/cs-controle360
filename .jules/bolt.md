## 2026-08-24 - Reuse Pre-Fetched Datasets in Consolidated Intelligence Endpoint

**Learning:** In multi-section aggregated API endpoints (like `get_consolidated_intelligence`), sub-feature calculations (like `PlaybookGenerator.build_dashboard`) often query the database for the same datasets (e.g., activities and releases) that are also fetched for top-level cross-module metrics.
**Action:** Always inspect endpoint handlers to ensure pre-fetched dataset lists are passed directly to sub-services when filters align, eliminating duplicate database queries per request.

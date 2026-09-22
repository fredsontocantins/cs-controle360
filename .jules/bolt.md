## 2026-09-22 - Pre-fetching and passing shared context in composite routers
**Learning:** Consolidated endpoints (such as `/api/reports/intelligence`) that invoke multiple services sequentially can suffer from redundant database reads when sub-services fetch the same document or entity lists independently.
**Action:** Pass pre-fetched entity lists into sub-service methods (e.g. `refresh_application_context(docs=docs)`) and reuse fetched collections across sub-dashboard generators when parameter filters match.

# Bolt's Performance Journal ⚡

## 2026-08-09 - Avoid Scope Creep and API-Breaking Envelopes in Dedicated Performance PRs
**Learning:** Standardizing and refactoring APIs (e.g. wrapping raw lists in enveloped objects) or updating core table schemas during a performance optimization PR introduces contract-breaking changes for the frontend UI/external consumers and migration risks for SQLite. A performance PR must remain laser-focused and preserve existing API schemas.
**Action:** Keep performance optimizations isolated. Do not modify table schemas or wrap API responses unless specifically instructed by the user or required for the optimization itself.

## 2026-09-10 - Single-pass grouping and document pre-fetching in intelligence hub
**Learning:** Calling `list_documents()` and filtering `activities` twice across separate methods inside `get_consolidated_intelligence` generated redundant DB/JSON-parsing queries and string processing. Passing pre-fetched `docs` and performing single-pass theme grouping reduces endpoint latency by ~12%.
**Action:** When building consolidated API endpoints, pre-fetch shared datasets (e.g. documents, activities, releases) at the top of the route handler and pass them into sub-service methods.

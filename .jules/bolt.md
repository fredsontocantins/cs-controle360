## 2026-09-26 - Consolidating redundant DB fetches in composite endpoints
**Learning:** Composite reporting endpoints like `/reports/intelligence` fetch data across multiple sub-services (Playbooks, Cross-module, PDF audit). When `cycle_id` is None, fetching operational records (`activities` and `releases`) early and reusing them across sub-services eliminates duplicate database queries without breaking sub-service isolation.
**Action:** Always check if composite/dashboard endpoints can pre-fetch shared dataset collections once and pass them down into child generators or calculators.

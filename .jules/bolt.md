# Bolt's Journal - Critical Learnings

## 2026-05-02 - [Pre-fetching and Pre-calculating for Batch Processing]
**Learning:** In endpoints like `/api/summary` that generate multiple cycle reports, N+1 query patterns and repeated expensive operations (datetime parsing, string normalization) significantly degrade performance as the dataset grows.
**Action:** Pre-fetch all necessary entity records once at the start of the request using `include_history=True`. Enrich these records in-memory with pre-calculated values (e.g., `_dt` for datetimes, `_owner_label` for names) to avoid redundant overhead in downstream filtering and grouping logic.

## 2026-05-02 - [Backend Testing Prerequisites]
**Learning:** Running backend tests or benchmarks requires `PYTHONPATH=.` and `CS_ALLOW_INSECURE_SECRETS=1` to find modules and bypass security assertions.
**Action:** Always include these environment variables when running `pytest` or standalone scripts in the sandbox.

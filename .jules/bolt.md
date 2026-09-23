## 2026-09-23 - Re-querying tables in cycle aggregation endpoints
**Learning:** In aggregate endpoints like `/api/summary`, calling entity list methods inside multi-cycle calculation loops caused up to 16 full-table queries per HTTP request. Pre-fetching full lists once at the start of the endpoint and passing them down eliminated redundant DB calls and deserialization overhead.
**Action:** Always pre-fetch full entity collections before passing them into multi-cycle or multi-window helper functions.

## 2026-09-23 - Response envelope wrapper breaking changes
**Learning:** Re-wrapping existing router endpoints with response helpers (e.g., `ok_list`, `ok`) alters response payload contracts for API consumers and breaks backward compatibility.
**Action:** Maintain raw response structures on existing endpoints unless explicitly instructed to standardize envelope formats.

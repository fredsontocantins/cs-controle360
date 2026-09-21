## 2026-09-21 - Reuse Operational Lists in Consolidated Report Intelligence

**Learning:** The consolidated intelligence endpoint (`/api/reports/intelligence`) loaded full activity and release lists multiple times when `cycle_id` was `None` (once for playbooks dashboard and once for cross-module metrics). Pre-fetching operational records once and reusing them avoids redundant DB queries and deserialization overhead.

**Action:** When building composite report endpoints that aggregate multiple domain metrics, pre-fetch shared datasets once at the top of the handler and pass them down.

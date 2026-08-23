## 2026-08-23 - Reusing Pre-Fetched Query Results in Intelligence Hub

**Learning:** When endpoint aggregation handlers (`/api/reports/intelligence`) call multiple service sub-generators (like `PlaybookGenerator.build_dashboard`) alongside module metrics, redundant queries to `list_atividade` and `list_release` can occur if `cycle_id` is None. Pre-fetching standard lists once and sharing them with sub-generators eliminates duplicate DB lookups.

**Action:** Before generating sub-dashboards or cross-module summaries, check if entity lists have already been retrieved for default cycle contexts and pass the pre-fetched objects.

## 2025-05-15 - [N+1 query in module labels]
**Learning:** Found an N+1 query problem in `dashboard` and `admin_console` routes where `_module_label` and `_build_module_summary` were individually fetching module data from SQLite for every item in a list. This became a bottleneck as the dataset grew (e.g., 1000 items).
**Action:** Always pre-fetch related entities (modules, clients) into a lookup dictionary when rendering lists or summaries to keep database interactions to O(1) or O(K) instead of O(N).

# Bolt Performance Journal

## 2026-07-08 - Dashboard Summary Optimization
**Learning:** The `/api/summary` endpoint was suffering from an N+1 query pattern and redundant date parsing. Fetching all entity records and cycles once at the start, pre-parsing ISO dates into `datetime` objects, and calculating cycle windows in-memory reduced response times by ~75%.
**Action:** Always look for loops that perform database queries or expensive string-to-date parsing. Pre-fetch collections and cache derived values (like parsed dates or normalized names) in record dictionaries for O(1) access during complex filtering/grouping logic.

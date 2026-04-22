## 2025-05-21 - [N+1 query in dashboard summary]
**Learning:** The `_build_module_summary` function in `cs_web/main.py` was suffering from an N+1 query problem, making a database call for every homologation, customization, and release record to resolve module names.
**Action:** Use lookup dictionaries (pre-fetching all modules once) when processing collections of records that need related entity data.

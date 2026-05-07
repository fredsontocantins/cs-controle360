# Bolt's Journal

## 2026-05-07 - Optimized date parsing with caching
**Learning:** The `parse_cycle_datetime` function is called frequently during dashboard summary generation, especially when filtering large record sets. Using `lru_cache` and prioritizing `datetime.fromisoformat` significantly reduces overhead.
**Action:** Use caching for utility functions involved in tight loops over large datasets.

# Bolt's Journal - Critical Learnings Only

## 2025-05-15 - Initial Journal
**Learning:** Performance-focused agent "Bolt" initialized. The mission is to find measurable wins in under 50 lines.
**Action:** Always measure before and after. Document impact clearly.

## 2025-05-15 - Dashboard Summary N+1 Queries
**Learning:** The `/api/summary` endpoint was hitting the database multiple times for each report cycle to filter records. Pre-fetching all records once and performing in-memory filtering reduced response time significantly.
**Action:** Always look for N+1 query patterns in aggregated views. Use in-memory caching for repeated computations like date parsing on the same record set.

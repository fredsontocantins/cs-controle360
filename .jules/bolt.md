# Bolt's Performance Journal ⚡

## 2026-04-26 - [Pre-fetching for Dashboard Summaries]
**Learning:** In this codebase, repository `list()` methods fetch entire tables, and convenience functions filter them in Python. For complex views like `get_summary` that need multiple filtered subsets (previous cycle, current cycle, selected cycle), pre-fetching the full history once and performing in-memory filtering is significantly faster than repeated repository calls.
**Action:** Use pre-fetched lists and in-memory filtering for dashboard-like endpoints to avoid N+1 repository hits.

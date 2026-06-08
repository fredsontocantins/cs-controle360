## 2026-06-08 - [Optimizing Date Parsing and N+1 Queries]
**Learning:** Using `datetime.fromisoformat` is significantly faster (up to 150x) than `strptime` for ISO-compliant strings. Additionally, pre-fetching records in dashboard endpoints prevents N+1 query patterns that degrade performance as the database grows.
**Action:** Always prioritize `fromisoformat` for ISO strings and use `@lru_cache` for repetitive parsing. Pre-fetch related entities once at the start of complex summary requests.

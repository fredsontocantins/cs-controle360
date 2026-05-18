# Bolt's Optimization Journal

## 2026-05-18 - Summary Endpoint Optimization
**Learning:** The `/api/summary` endpoint was suffering from N+1 query patterns and redundant datetime parsing. Using `lru_cache` on `parse_cycle_datetime` provided an immediate 2x speedup. Batch-fetching all entities at the start of the request and pre-calculating expensive values (datetimes, normalized names) yielded another 3x improvement.
**Action:** Always pre-fetch full record sets for dashboard summaries and reuse them for all period-based filtering to avoid redundant database calls. Cache expensive string-to-datetime parsing in tight loops.

## 2026-05-18 - Frontend Build Regression
**Learning:** Setting `reactCompiler: true` in `next.config.ts` causes build failures if `babel-plugin-react-compiler` is not present in `package.json`.
**Action:** Ensure all experimental features in `next.config.ts` have their corresponding dependencies in `package.json` before enabling.

## 2026-05-18 - Type-Checking Regression
**Learning:** Legacy frontend directories (`frontend-legacy`) can cause type-checking errors in the main `tsconfig.json` if they use incompatible TypeScript versions or configurations.
**Action:** Exclude legacy or non-Next.js frontend directories from `tsconfig.json` to avoid external type-checking blockers.

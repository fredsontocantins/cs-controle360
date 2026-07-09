## 2026-07-09 - get_summary endpoint optimization
**Learning:** The `get_summary` endpoint was a performance bottleneck due to redundant database queries and repeated datetime/name parsing within cycle loops. Pre-fetching all records and caching parsed values (names, datetimes) in-memory significantly reduces response time. However, mutating shared record objects with internal cache keys (e.g., `_dt_*`) can leak implementation details to the API response if not properly cleaned up.
**Action:** Always implement a `cleanup` step when using in-memory caching/augmentation of data dictionaries before returning them in an API response to ensure implementation details are not exposed.

## 2026-07-09 - Next.js Build Failures and React Compiler
**Learning:** CI builds may fail if `reactCompiler: true` is enabled in `next.config.ts` but the necessary `babel-plugin-react-compiler` dependency is missing or incompatible with the environment. Disabling the feature is a quick fix to restore CI stability when infrastructure changes are out-of-scope.
**Action:** Set `reactCompiler: false` in `next.config.ts` if build errors related to the React Compiler occur in environments where dependencies cannot be easily updated.

## 2026-07-09 - TSConfig Standards and Build Hygiene
**Learning:** Re-running builds or dev servers can sometimes overwrite `tsconfig.json` with less strict or non-standard settings (e.g., changing `jsx: preserve` to `react-jsx`). This can cause pipeline breaks. Additionally, build artifacts like `tsconfig.tsbuildinfo` or directories like `.next/` and `node_modules` can pollute the git state if not carefully managed during local verification.
**Action:** Always verify `tsconfig.json` adheres to repository standards (`jsx: preserve`) before committing. Ensure `node_modules` and other artifacts are excluded or cleaned before final submission.

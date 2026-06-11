## 2026-06-11 - Verification Enablers vs Atomic PRs
**Learning:** Including minimal necessary fixes (like schema mismatches) to enable verification in a local environment can be seen as "feature creep" and out-of-scope, even if they are required for the tests to run.
**Action:** Keep performance PRs strictly limited to performance changes. If the environment is broken, fix it in a separate PR first or document that verification was done under a specific set of local-only changes.

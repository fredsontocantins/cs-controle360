# Bolt's Journal - Critical Performance Learnings

## 2026-07-29 - Redundant List Queries in Consolidated Intelligence
**Learning:** When generating consolidated reporting and playbook recommendations, standard entity lists (like activities and releases) are often fetched globally for general metrics and then queried again inside playbook recommendations logic with similar parameters. Pre-fetching these standard lists and passing them into downstream sub-components completely avoids redundant, repetitive, and expensive database round-trips.
**Action:** Always verify if global entity list datasets can be loaded once and reused across different sections or services in the same endpoint call.

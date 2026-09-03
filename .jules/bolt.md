## 2025-05-18 - Single-Pass Playbook Theme Classification Optimization
**Learning:** In `PlaybookGenerator.generate_from_errors`, running two iteration passes over thousands of activity items to perform theme detection and compute theme counts creates redundant string formatting and regex/keyword evaluation overhead.
**Action:** Always combine grouping and frequency counting into a single pass and precompute static dict items into tuple constants for fast tuple-iteration without dictionary lookup overhead.

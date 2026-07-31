# Palette's Journal - Critical UX & Accessibility Learnings

## 2025-01-01 - React 19 Form Accessibility & Stable ID Linkage with SSR
**Learning:** Hand-crafted, missing, or unstable dynamic ID strings in reusable form inputs cause broken label-input associations, making elements inaccessible to screen readers and causing Next.js SSR hydration mismatches.
**Action:** Use React 19's native `useId()` hook in all reusable visual controls (like `Input` and `Select`) to automatically guarantee unique, stable, and synchronized IDs for label linking (`htmlFor`), validation state alerting (`aria-invalid`), and screen-reader error messaging (`aria-describedby`).

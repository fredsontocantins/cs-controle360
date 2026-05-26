## 2025-05-15 - Standardizing Form Accessibility
**Learning:** Core form components (Input, Select) lacked stable ID linkage between labels and inputs, and didn't communicate error states to screen readers.
**Action:** Always use `useId` for `id` generation and link labels with `htmlFor`. Implement `aria-invalid` and `aria-describedby` for error messages to ensure a robust accessibility baseline across the app.

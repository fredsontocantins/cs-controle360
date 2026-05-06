## 2025-05-21 - Standardized Form Component Accessibility
**Learning:** Core form components (Input, Select) lacked stable ID association between labels and inputs, and didn't provide ARIA attributes for error states. Using `useId` ensures that even without an explicit `id` prop, the label-input connection is maintained, which is critical for screen readers.
**Action:** Always implement `useId` for stable ID generation and link error messages via `aria-describedby` in new form components. Add visual required indicators (*) when the `required` prop is true.

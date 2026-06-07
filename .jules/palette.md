## 2025-05-22 - Enhanced Form Accessibility
**Learning:** Core form components (Input, Select) must use React's `useId` for robust label-input linkage when no explicit ID is provided. Implementing `aria-invalid`, `aria-describedby` for error states, and `aria-required` for mandatory fields significantly improves the experience for screen reader users.
**Action:** Always use `useId` for stable linking and implement standard ARIA attributes for form states (error, required, disabled) in any new or modified input components.

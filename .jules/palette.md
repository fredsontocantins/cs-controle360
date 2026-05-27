
## 2025-05-14 - Standardized Form Component Accessibility
**Learning:** Core form components (Input, Select) should always use React's `useId` for robust label-input linkage and implement `aria-invalid` and `aria-describedby` for error message accessibility. Visual "required" indicators should be hidden from screen readers using `aria-hidden="true"`.
**Action:** Apply this pattern to all new form components and audit existing ones.

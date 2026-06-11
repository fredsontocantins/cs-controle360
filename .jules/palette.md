## 2025-05-14 - Accessibility improvements for form components and sidebar
**Learning:** Core form components (Input, Select) must use React's `useId` for robust label-input linkage and implement `aria-invalid` and `aria-describedby` for error message accessibility. Decorative icons should be hidden from screen readers using `aria-hidden="true"`.
**Action:** Implement these patterns in all new UI components and audit existing ones for consistency.

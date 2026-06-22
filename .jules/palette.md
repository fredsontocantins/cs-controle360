## 2025-05-15 - Form and Navigation Accessibility Polish
**Learning:** Core form components (Input, Select) must use React's `useId` for robust label-input linkage and implement `aria-invalid` and `aria-describedby` for error message accessibility. Decorative icons in navigation should be hidden from screen readers to reduce verbosity.
**Action:** Always implement `useId` for stable IDs and use ARIA attributes (`aria-describedby`, `aria-invalid`, `aria-hidden`) to ensure the UI is accessible and intuitive for all users.

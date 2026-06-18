## 2025-05-15 - Accessible Form Components Pattern
**Learning:** Core form components (Input, Select) must use React's `useId` for robust label-input linkage and implement `aria-invalid` and `aria-describedby` for error message accessibility. Use `${id}-error` for error IDs.
**Action:** Use `useId` to generate stable IDs if not provided, and always link error messages to inputs using `aria-describedby`.

## 2025-05-15 - Decorative Icon Accessibility
**Learning:** Decorative icons in navigation links (Sidebar) should be hidden from screen readers to prevent redundant announcements.
**Action:** Add `aria-hidden="true"` to icons that are adjacent to descriptive text labels.

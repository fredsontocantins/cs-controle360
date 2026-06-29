## 2025-05-21 - Accessible Form and Sidebar Patterns
**Learning:** Core form components must use React's `useId` for robust label-input linkage and implement `aria-invalid` and `aria-describedby` (using `${id}-error`) with `role="alert"` for accessible error reporting. Additionally, decorative icons in navigation elements should include `aria-hidden="true"` to prevent redundant announcements by screen readers.
**Action:** Apply these patterns to all base UI components and navigation layouts to ensure the application remains screen-reader friendly and intuitive.

## 2025-05-14 - Core Form Component Accessibility
**Learning:** Core form components (Input, Select) must use React's `useId` for robust label-input linkage and implement `aria-invalid` and `aria-describedby` for error message accessibility.
**Action:** Always include these accessibility patterns when creating or modifying form-related components.

## 2025-05-14 - Decorative Icons in Navigation
**Learning:** Decorative icons in sidebar and navigation links should have `aria-hidden="true"` to prevent screen readers from announcing them as separate elements, which can be redundant and confusing.
**Action:** Apply `aria-hidden="true"` to all purely decorative icons in navigation menus.

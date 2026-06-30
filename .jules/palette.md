## 2026-06-30 - Accessible Form Component Patterns
**Learning:** Core form components must use React's `useId` for stable label-input linkage and implement `aria-invalid` and `aria-describedby` (linking to `${id}-error`) for screen reader accessibility. Visual required indicators should be decorative (`aria-hidden="true"`) to avoid redundant announcements.
**Action:** Apply these patterns consistently across all form-related components like Input and Select.

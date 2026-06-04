## 2025-05-15 - Standardizing Form Component Accessibility
**Learning:** Core form components (Input, Select) must use React's `useId` for robust label-input linkage and implement `aria-invalid` and `aria-describedby` for error message accessibility. Adding a visual `*` for required fields that is hidden from ARIA improves clarity without redundant screen reader announcements.
**Action:** Use the pattern established in `components/ui/input.tsx` and `components/ui/select.tsx` for all future form-related components.

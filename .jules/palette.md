## 2025-05-15 - Form Component Accessibility
**Learning:** Standardized form components like `Input` and `Select` require explicit ARIA attributes (`aria-invalid`, `aria-describedby`) and `role="alert"` for error messages to ensure they are accessible to screen reader users. Additionally, a visual indicator for required fields that is hidden from screen readers prevents redundant announcements while helping sighted users.
**Action:** Always include ARIA mapping and explicit error roles when building or extending reusable form components.

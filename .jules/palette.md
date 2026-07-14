## 2025-05-15 - Accessible Form Components Pattern
**Learning:** Standardizing accessibility in form components (Input, Select) requires stable ID linkage, clear visual/aria indicators for required fields, and proper ARIA attributes (aria-invalid, aria-describedby) to connect inputs with their error states for screen readers.
**Action:** Always use `useId` for stable accessibility linkage and implement `aria-invalid`, `aria-describedby` (linking to error message ID), and `role="alert"` on error messages in reusable form components.

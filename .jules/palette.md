## 2026-07-06 - [Form Accessibility Pattern]
**Learning:** Found that core form components (Input, Select) lacked visual indicators for required fields and proper ARIA linkage for error states.
**Action:** Implemented a standard pattern: visual asterisk for `required`, `aria-invalid` based on error presence, and `aria-describedby` linked to a `role="alert"` error message. This should be applied to all future form components.

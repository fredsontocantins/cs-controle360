## 2025-05-30 - Standardized Accessible Form Components
**Learning:** Core form components (Input, Select) were missing stable IDs for label-input linkage and ARIA attributes for error state communication.
**Action:** Always use React's `useId` for unique IDs and implement `aria-invalid` and `aria-describedby` to link inputs with error messages. Added visual `*` indicator (hidden from ARIA) for required fields.

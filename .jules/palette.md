## 2026-07-10 - Standardized Form Accessibility Pattern
**Learning:** Using React's `useId` hook ensures stable and unique IDs for label-input pairing, which is crucial for screen reader accessibility. Combining this with `aria-invalid`, `aria-describedby`, and visual `required` indicators creates a robust and intuitive form experience.
**Action:** Always implement `useId`, `aria-invalid`, and `aria-describedby` in shared form components (Input, Select, etc.) to ensure consistent accessibility across the application.

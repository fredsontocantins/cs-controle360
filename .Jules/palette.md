## 2025-05-14 - Standardizing Accessibility in Form Components
**Learning:** Adding `aria-invalid` and `aria-describedby` to Input and Select components ensures that screen readers correctly associate error messages with their respective fields. Automated ID generation using `useId` prevents ID collisions in complex forms.
**Action:** Always use `useId` for form field IDs and link error messages via `aria-describedby` when implementing or updating UI components.

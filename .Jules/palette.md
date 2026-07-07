## 2025-07-07 - Accessible Form Pattern
**Learning:** For robust accessibility in form components, manual ID management is error-prone. Using React 19's `useId` hook ensures stable, unique IDs that reliably link labels to inputs and `aria-describedby` to error messages, even in hydrated environments.
**Action:** Always implement `useId` in reusable form components (Input, Select, Checkbox) to handle accessibility associations automatically and prevent ID collisions.

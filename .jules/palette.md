## 2025-05-15 - [Form Component Accessibility]
**Learning:** Standardized form components (like Input) should implement `aria-invalid`, `aria-describedby` (linking to `${id}-error`), and use `role="alert"` for error messages to ensure screen reader compliance. Stable ID generation via `useId` is critical for reliable label-input association in SSR/hydration environments.
**Action:** Always include these accessibility attributes when creating or updating form components.

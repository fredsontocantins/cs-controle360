## 2025-05-15 - [Form Component Accessibility]
**Learning:** Standardized form components (Input, Select) should implement `aria-invalid`, `aria-describedby` (linking to `${id}-error`), and use `role="alert"` for error messages to ensure screen reader compliance. Stable ID generation via `useId` is critical for reliable label-input association in SSR/hydration environments.
**Action:** Always include these accessibility attributes when creating or updating form components.

## 2025-05-15 - [Decorative Icon Management]
**Learning:** Decorative icons in navigational elements (like Sidebar) can create noise for screen reader users if they are not explicitly hidden.
**Action:** Add `aria-hidden="true"` to all decorative/purely visual icons.

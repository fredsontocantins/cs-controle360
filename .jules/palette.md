## 2025-05-15 - [Form Accessibility Pattern]
**Learning:** Core form components (Input, Select) were missing stable IDs and ARIA attributes for linking labels and error messages. Using `useId` and `aria-describedby` ensures a consistent, accessible experience for screen reader users.
**Action:** Always use the `Input` and `Select` components which now handle these accessibility concerns automatically, and ensure the `required` prop is used for visual and programmatic validation.

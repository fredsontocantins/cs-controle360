## 2025-05-22 - Accessibility Enhancements for Form Components
**Learning:** Core form components (Input, Select) must use React's `useId` for stable label linkage and implement `aria-invalid` and `aria-describedby` (pointing to `${id}-error`) for consistent screen reader announcements across various browser/AT combinations.
**Action:** Always implement these ARIA attributes and stable ID patterns in reusable form components to ensure baseline accessibility without requiring manual ID management by the consumer.

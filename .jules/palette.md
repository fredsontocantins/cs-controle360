# Palette's Journal

## 2025-05-24 - Base UI Accessibility Foundation
**Learning:** Core components like `Input` were missing automatic ID generation for labels and `aria-describedby` for error states, leading to inconsistent accessibility across forms.
**Action:** Always use `useId` for stable component IDs and ensure error messages are programmatically linked to inputs.

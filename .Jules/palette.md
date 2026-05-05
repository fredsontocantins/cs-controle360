# Palette's Journal - Critical UX Learnings

## 2025-05-14 - Standardizing Form Accessibility
**Learning:** Core UI components (Input, Select) lacked stable IDs and proper ARIA associations between labels, inputs, and error messages, which hindered screen reader accessibility.
**Action:** Implement `useId` for stable IDs and use `aria-describedby` and `aria-invalid` to link inputs with their descriptive content and states.

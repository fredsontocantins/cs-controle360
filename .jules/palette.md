# Palette Journal - UX & Accessibility Learnings

## 2025-05-15 - Standardizing Form Accessibility
**Learning:** Core form components (Input, Select) should always use React's `useId` for robust label-input linkage and implement `aria-invalid` and `aria-describedby` for error message accessibility. Decorative icons should be hidden from screen readers.
**Action:** Implement `useId`, `aria-invalid`, `aria-describedby`, and `aria-hidden` in all base UI components that involve user interaction or decorative graphics.

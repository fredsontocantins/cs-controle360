# Palette's Journal - Critical UX/a11y Learnings

## 2025-05-14 - Initial Setup
**Learning:** Initialized the journal to record critical UX and accessibility insights for the CS Controle 360 project.
**Action:** Use this file to document reusable patterns and specific constraints discovered during development.

## 2025-05-14 - Accessibility for Form Components and Navigation
**Learning:** Form components (Input, Select) need stable, unique IDs for labels and ARIA descriptions to be accessible. Navigation links must indicate the current page semantically.
**Action:** Use React's `useId` to generate stable IDs and link labels/errors via `htmlFor`, `aria-describedby`, and `aria-invalid`. Apply `aria-current="page"` to active navigation links.

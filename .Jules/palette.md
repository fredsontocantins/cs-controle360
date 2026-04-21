## 2026-04-21 - [Automatic Required Field Indicators]
**Learning:** Using the CSS `:has()` selector allows for clean, maintainable, and automatic labeling of required fields across an entire application without needing to manually add classes or asterisks to every template. It leverages semantic HTML (`required` attribute) to provide visual cues.
**Action:** When working on forms, prefer using `.form-field label:has(+ [required])::after` to add visual "required" indicators, ensuring consistent UX with zero template overhead.

## 2026-04-21 - [Accessible Dashboard Links]
**Learning:** When wrapping informational cards in anchor tags, `aria-label` should include the dynamic data displayed within the card. If a simple `aria-label` like "View details" is used, screen readers may skip the actual counts or values shown on the card, making the dashboard less useful for those users.
**Action:** Use descriptive `aria-label` templates like `Label: {{ count }} description. View details.` to ensure both the action and the current state are communicated to assistive technologies.

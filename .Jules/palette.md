# Palette's Journal - CS Controle 360º

## 2025-05-14 - Visual Indicators for Required Fields
**Learning:** In forms with many optional fields, users can become frustrated if they only discover which fields are mandatory after a failed submission. Using the CSS `:has()` selector allows for a clean, logic-free way to mark required fields globally.
**Action:** Use `.form-field:has(input[required]) label::after` to append a visual cue (e.g., a red asterisk) to labels of required inputs without modifying every template.

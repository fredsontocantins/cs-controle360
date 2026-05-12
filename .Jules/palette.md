## 2025-05-15 - [Accessible Form Primitives]
**Learning:** Found that base form components (Input, Select) were missing stable ID generation and ARIA associations between labels, inputs, and error messages.
**Action:** Use React's `useId` to generate stable IDs and link them using `htmlFor`, `aria-invalid`, and `aria-describedby`. Add visual 'required' indicators (\*) that are hidden from screen readers to avoid redundancy with the `required` attribute.

## 2025-05-03 - [Standardized Loading States]
**Learning:** Adding a standardized `isLoading` prop to the core `Button` component ensures consistent visual feedback and accessibility (via `aria-busy`) across the application, preventing users from double-submitting forms.
**Action:** Always use the `Button` component's `isLoading` prop for asynchronous actions instead of manual conditional rendering of text or spinners.

## 2025-05-18 - Loading States and Focus Accessibility on Action Buttons

**Learning:** Adding `isLoading` to reusable `Button` components ensures consistent visual feedback (spinner animation) and programmatic accessibility (`aria-busy="true"`, `disabled` state) during asynchronous operations across the application. Combining this with `focus-visible:ring-2` ensures keyboard focus indicators remain visible without creating focus ring outline artifacts on mouse clicks.
**Action:** Always include an `isLoading` prop on base Button components with built-in `aria-busy` and `focus-visible` styling when designing core UI primitives.

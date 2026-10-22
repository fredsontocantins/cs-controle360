## 2025-05-18 - Accessible Loading States and Live Alert Regions

**Learning:** Buttons handling async tasks (like form submission) need both visual spinner indicators and `aria-busy="true"` to communicate loading state to visual users and screen readers. Additionally, error messages rendered conditionally below forms must include `role="alert"` and `aria-live="polite"` so screen readers immediately announce authentication or validation failures without requiring manual focus navigation.

**Action:** Whenever adding or using submit buttons with pending state, pass `isLoading` to set `aria-busy` and render accessible spinners. Always wrap conditional form error messages with `role="alert"`.

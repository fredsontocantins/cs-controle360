## 2025-05-18 - Accessible Loading States for Action Buttons
**Learning:** Adding an `isLoading` prop to shared UI buttons ensures consistent visual (`Loader2` spinner) and screen reader (`aria-busy="true"`) loading feedback across form submissions while preventing double submission through automatic element disabling.
**Action:** Use `isLoading={loading}` on core primary action buttons (e.g., login, form submits) instead of raw text replacements like `disabled={loading}`.

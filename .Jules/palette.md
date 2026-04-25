## 2025-05-15 - Standardized Button Loading Pattern
**Learning:** Standardizing loading states in a base component (Button) reduces cognitive load for users by providing consistent visual feedback across the app. Using `aria-busy` and `aria-hidden` on the spinner ensures the interaction is clear for screen reader users without redundant announcements.
**Action:** Always prefer the `isLoading` prop on the base `Button` component over manual conditional rendering for async actions.

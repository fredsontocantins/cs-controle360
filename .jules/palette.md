## 2025-05-18 - Loading States & ARIA Busy on Action Buttons
**Learning:** Simply changing button text during async operations (e.g., "Entrando...") without setting `aria-busy="true"` or providing an animated visual cue leaves screen reader users and visual users with incomplete feedback about pending state and can lead to accidental double submissions.
**Action:** Always provide an explicit `isLoading` prop on base `Button` components that handles disabling interaction, rendering an animated `Loader2` spinner icon, and setting `aria-busy="true"` automatically.

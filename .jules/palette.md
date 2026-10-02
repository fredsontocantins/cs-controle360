# Palette's UX & Accessibility Journal

## 2025-05-18 - Accessible Async Button Loading States & Focus Ring Refinement
**Learning:** Icon-only or text buttons undergoing async operations without explicit `aria-busy="true"`, visual loading spinners, and disabled states leave screen reader users unaware of ongoing background actions and lead to accidental duplicate submissions. Additionally, standard `focus:` outlines trigger unwanted focus rings on mouse click; using `focus-visible:` retains high contrast keyboard focus indicators while avoiding mouse click visual noise.
**Action:** Always provide an `isLoading` prop on base `Button` components that sets `aria-busy="true"`, renders an animated `Loader2` spinner with `aria-hidden="true"`, disables interaction, and uses `focus-visible:ring-2` styling.

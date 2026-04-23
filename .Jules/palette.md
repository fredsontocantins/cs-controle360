## 2025-04-23 - [Modal Accessibility & Button Feedback]
**Learning:** Icon-only buttons (like the close 'X' in modals) are often overlooked for accessibility. Adding `aria-label` is a simple but high-impact win for screen readers. Centralizing loading states in a shared component like `Button` significantly reduces boilerplate and ensures consistent feedback across the app.
**Action:** Always check for icon-only buttons during UX sweeps. Prefer adding `isLoading` props to UI components rather than manual ternary logic at the call-site.

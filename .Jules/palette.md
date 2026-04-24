## 2026-04-24 - [Standardized Loading Pattern for Buttons]
**Learning:** Inconsistent loading states (manual text changes vs. dedicated props) lead to disjointed UX and accessibility gaps. A core `Button` component should natively handle `isLoading` to ensure uniform visual feedback (spinners) and automatic interaction prevention (`disabled` state).
**Action:** Use the `isLoading` and `loadingText` props on the `Button` component for all asynchronous operations to maintain consistency and improve screen reader feedback.
